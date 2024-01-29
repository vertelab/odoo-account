from odoo import models, fields, api, _
import requests, time, json, logging, datetime, base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):

    _inherit = 'res.partner'

    is_saltedge_api = fields.Boolean("Enable Saltedge API")

    saltedge_api_url = fields.Char("API URL")

    saltedge_client_id = fields.Char("Client ID")

    saltedge_secret = fields.Char("Secret")

    saltedge_redirect_url = fields.Char("Redirect URL")

    saltedge_private_key = fields.Text("Private Key")

    saltedge_connection_id = fields.Char("Established Session ID")

    expires_at = str(int(time.time() + 60))


    def _create_signature(self,method: str,url: str, data = "", file = ""):

        private_key = self.saltedge_private_key.encode("utf-8")

        private_key = serialization.load_pem_private_key(private_key, password=None ,backend=default_backend())

        signature_string = f'{self.expires_at}|{method}|{url}|{"" if data == "" else f"{data}"}{"" if file == "" else f"|{file}|"}'

        signature = private_key.sign(signature_string.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())

        signature_as_base64 = base64.b64encode(signature).decode("utf-8")

        return signature_as_base64


    def customer_requests(self):

        customer_ids = []

        customers_url = self.create_url("customers")

        headers = self.create_headers(method="GET",content_type="application/x-www-form-urlencoded",url=customers_url)

        customer_response = requests.get(customers_url, headers=headers)
        
        if customer_response.status_code == 200:

            customer_response = json.loads(customer_response.text)["data"]

            for customer in customer_response:

                customer_id = customer["id"]

                customer_ids.append(customer_id)

            return customer_ids
        
        _logger.error(customer_response.text)

        raise ValidationError("failed to get customers")
    
    
    def create_token(self, customer):

        token_url = self.create_url("oauth_providers/create")

        payload = json.dumps({ 
                    "data": { 
                        "customer_id": f"{customer}", 
                        "country_code": "XF", 
                        "provider_code": "fakebank_oauth_xf",
                        "return_connection_id": True,
                        "consent": { 
                            "scopes": [ 
                                "account_details", 
                                "transactions_details" 
                            ], 
                            "from_date": f"{datetime.datetime.today()}"
                        }, 
                        "attempt": { 
                            "return_to": self.saltedge_redirect_url + "/account/saltedge/return", 
                            "from_date": f"{datetime.datetime.today()}", 
                            "fetch_scopes": [ 
                                "accounts", 
                                "transactions" 
                            ] 
                        }, 
                    }
                })
        
        headers = self.create_headers("POST",url=token_url, payload=payload)

        token_response = requests.post(token_url, data=payload, headers=headers)

        return token_response
        

    def reconnect_token(self):

        token_reconnect_url = self.create_url("oauth_providers/reconnect")

        payload = json.dumps({ 
                "data": { 
                    "connection_id": self.saltedge_connection_id, 
                    "consent": { 
                    "scopes": [ 
                        "account_details", 
                        "transactions_details" 
                    ], 
                    "from_date": f"{datetime.datetime.today()}" 
                    }, 
                    "attempt": { 
                    "return_to": self.saltedge_redirect_url + "/account/saltedge/return"
                    }, 
                    "include_fake_providers": True,
                    "return_connection_id": True
                } 
                })

        headers = self.create_headers("POST", url=token_reconnect_url, payload=payload)

        token_reconnect_response = requests.post(token_reconnect_url, data=payload, headers=headers)

        return token_reconnect_response
    

    def action_sync_transactions_with_saltedge(self): return self._get_response_values()
            

    def establish_session(self):

        customers = self.customer_requests()

        response = ""

        for customer in customers:
        
            response = self.reconnect_token()

            json_response = response.json() 

            if response.status_code != 200:                

                _logger.error(f"Error: {json_response['error']['class']} | Message: {json_response['error']['message']}")
            
                response = self.create_token(customer)

                json_response = response.json()
                
                if response.status_code != 200:

                    json_response = json_response["error"]

                    _logger.error(f"Error: {json_response['class']} | Message: {json_response['message']}")

                    raise ValidationError("Failed to create a oauth session on Saltedge.")

        return response.json()


    def _get_response_values(self):

        response = self.establish_session()

        response = response["data"]
        
        token = response["token"]

        self.saltedge_connection_id = response["connection_id"]

        return response
    
    
    def create_headers(self, method, url, accept="application/json", content_type = "application/json", payload=""):

        headers= {
            "Accept": accept,
            "Content-type": content_type,
            "App-id": self.saltedge_client_id,
            "Secret": self.saltedge_secret,
            "Expires-at": self.expires_at
        }

        headers["Signature"] = self._create_signature(method,url,payload)

        return headers


    def create_url(self,url_param: str):

        url = self.saltedge_api_url

        if "/api/v5" not in url:

            url = url + "api/v5/" if url[-1] == "/" else url + "/api/v5/"

        url = url if url[-1] == "/" else url + "/"

        return url + url_param


    def get_accounts(self):

            account_url = self.create_url(f"accounts?connection_id={self.saltedge_connection_id}")

            headers = self.create_headers("GET", account_url)

            account_response = requests.get(account_url, headers=headers)

            if account_response.status_code != 200:

                account_response = account_response.json()["error"] 

                _logger.error(f"Error: {account_response['class']} | Message: {account_response['message']}")

                if "RequestExpired" in account_response:
                                        
                    self.establish_session()
                    
                    return self.get_accounts()

                raise ValidationError("faild to get accounts")
            
            return account_response.json()["data"]

            
    