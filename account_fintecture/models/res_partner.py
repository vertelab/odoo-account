from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging, time, email, uuid, base64, hashlib, requests, json
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.Model):
    _inherit = 'res.partner'

    is_fintecture_api = fields.Boolean("Enable Fintecture API")

    fintecture_app_id = fields.Char("Application ID")

    fintecture_app_secret = fields.Char("Application Secret")

    fintecture_redirect_url = fields.Char("Redirect URL")

    fintecture_private_key = fields.Text("Private Key")

    fintecture_access_token = fields.Char("Access Token")

    fintecture_refresh_token = fields.Char("Refresh Token")


    def create_url(self,params):

        url = "https://api-sandbox.fintecture.com"

        if url[-1] == "/":

            url = url[:-1]

        return url + params


    def _create_authorization_header(self,authorization):

        if authorization.lower() == "basic":

            app_secret_and_id = f"{self.fintecture_app_id}:{self.fintecture_app_secret}".encode("utf-8")

            base64_encoded_app_secret_and_id = base64.b64encode(app_secret_and_id).decode("utf-8")

            return "Basic {" + f"{base64_encoded_app_secret_and_id}" + "}"
        
        return f"Bearer {authorization}"
 

    def create_signing_string(self,method,url_params,date,x_request_id,payload):

        request_target = f"{method} {url_params}"

        if payload != "":

            digest = self.create_digest(payload)

        signing_string = f"(request-target): {request_target}\ndate: {date}" + (f"\ndigest: SHA-256={digest}\nx-request-id: {x_request_id}" if payload != "" else f"\nx-request-id: {x_request_id}")
        
        _logger.error(signing_string)

        return signing_string


    def create_digest(self,payload):

        payload = json.dumps(payload, separators=(',', ':'))

        hash_payload = hashlib.sha256(payload.encode("utf-8"))

        base64_digest = base64.b64encode(hash_payload.digest())

        return base64_digest.decode("utf-8")


    def create_payload_from_url(self,url_params):

        list_of_params = url_params.split("?")[1].split("&")

        payload = dict()

        for param in list_of_params:

            param = param.split("=")

            print(f"{param[0]} {param[1]}")

            payload[param[0]] = param[1]

        return 


    def create_signature(self,method, url_params, date, x_request_id, payload=""):

        if "?" in url_params:

            payload = self.create_payload_from_url(url_params)

        signing_string = self.create_signing_string(method,url_params,date,x_request_id,payload)

        private_key = self.fintecture_private_key.encode("utf-8")

        private_key = serialization.load_pem_private_key(private_key, password=None)

        signature = private_key.sign(signing_string.encode("utf-8"), padding.PKCS1v15(), algorithm=hashes.SHA256())

        signature_as_base64 = base64.b64encode(signature).decode("utf-8")

        signing_string = signing_string.replace("\n"," ")

        signature_string = f'keyId="{self.fintecture_app_id}",algorithm="rsa-sha256",headers="(request-target) date {"" if payload == "" else "digest"} x-request-id",signature="{signature_as_base64}"'

        return signature_string

       
    def create_headers(self,accept="application/json", content_type="application/x-www-form-urlencoded", is_app_id = True, authorization = None, signature = False, method = "get", url_params = "", payload = ""):

        headers = {
            "accept": accept,
            "content-type": content_type
        }

        if is_app_id:

            headers["app_id"] = self.fintecture_app_id

        if authorization:

            headers["authorization"] = self._create_authorization_header(authorization)

        if signature:

            date = email.utils.formatdate(time.time()).replace("-0000","GMT")
            x_request_id = str(uuid.uuid4())

            headers["x-request-id"] = x_request_id
            headers["date"] = date
            headers["signature"] = self.create_signature(method,url_params,date,x_request_id,payload)

        return headers
    

    def get_provider_authorization(self,bank_id):

        url_params = f"/ais/v1/provider/{bank_id.provider_code}/authorize?response_type=code&redirect_uri={self.fintecture_redirect_url + '/account/fintecture/return'}&state=1234&model=redirect"

        url = self.create_url(url_params)

        headers = self.create_headers(signature=True,url_params=url_params)

        response = requests.get(url,headers=headers)

        return response.json()
    

    def oauth_authenticate(self, code=""):

        if self.fintecture_refresh_token:

            response = self.refresh_access_token()

            response_json = response.json()

            if response.status_code == 200:

                self.fintecture_access_token = response_json["access_token"]

                return

            _logger.error(f"Error response {response_json['code']}: {response_json['errors'][0]['message']}")

        response = self.get_access_token(code)

        response_json = response.json()

        if response.status_code != 200:

            _logger.error(f"Error response {response_json['code']}: {response_json['errors'][0]['message']}")
                
            raise ValidationError("Failed to get a access token")


    def get_access_token(self,code):

        url = self.create_url("/oauth/accesstoken")

        payload = {
            "grant_type": "authorization_code",
            "scope": "AIS",
            "code": code
        }

        headers = self.create_headers(is_app_id=False,authorization="basic")

        response = requests.post(url, data=payload, headers=headers)

        _logger.error(response.text)

        if response.status_code == 200:

            response = response.json()

            self.fintecture_access_token = response["access_token"]

            self.fintecture_refresh_token = response["refresh_token"]

        return response


    def refresh_access_token(self):

        url = self.create_url("/oauth/refreshtoken")

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.fintecture_refresh_token
        }

        headers = self.create_headers(is_app_id=False,authorization="basic") 

        response = requests.post(url, data=payload, headers=headers)

        _logger.error(response.text)

        return response


    def get_accounts(self,code,customer_id):

        self.get_access_token(code)

        url_params = f"/ais/v1/customer/{customer_id}/accounts"

        url = self.create_url(url_params)

        headers = self.create_headers(authorization=self.fintecture_access_token,signature=True,url_params=url_params)

        response = requests.get(url, headers=headers)

        _logger.error(response.text)

        return response
    
    
    def get_account_transactions(self,customer_id,fintecture_account_id,timespan):
        
        self.oauth_authenticate()

        #url_params = f"/ais/v1/customer/{customer_id}/accounts/{fintecture_account_id}/transactions?remove_nulls=true&convert_dates=false&filter[date_from]={timespan['date_from']}&filter[date_to]={timespan['date_to']}"
        url_params = f"/ais/v1/customer/customer_id/accounts/account_id/transactions?remove_nulls=true&convert_dates=false&filter[date_to]={timespan['date_to']}&filter[date_from]={timespan['date_from']}&raw=false"

        #url_params = f"/ais/v1/customer/{customer_id}/accounts/{fintecture_account_id}/transactions"

        url = self.create_url(url_params)

        headers = self.create_headers(authorization=self.fintecture_access_token,signature=True,url_params=url_params)
  
        response = requests.get(url, headers=headers)

        _logger.error(response.text)

        return response
