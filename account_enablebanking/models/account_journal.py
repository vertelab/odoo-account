from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timezone, timedelta
import jwt as pyjwt
import requests
from pprint import pprint
from urllib.parse import urlparse, parse_qs
import werkzeug
import uuid


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def request_essentials(self):
        api_url = self.env['ir.config_parameter'].get_param('enablebanking.api_url')
        private_key = self.env['ir.config_parameter'].get_param('enablebanking.private_key')
        application_id = self.env['ir.config_parameter'].get_param('enablebanking.application_id')

        iat = int(datetime.now().timestamp())
        jwt_body = {
            "iss": "enablebanking.com",
            "aud": "api.enablebanking.com",
            "iat": iat,
            "exp": iat + 3600,
        }
        jwt = pyjwt.encode(
            jwt_body,
            private_key,
            algorithm="RS256",
            headers={"kid": application_id}, )

        base_headers = {"Authorization": f"Bearer {jwt.decode('utf-8')}"}
        return api_url, private_key, application_id, base_headers

    def action_sync_transactions_with_enable_banking(self):
        api_url, private_key, application_id, base_headers = self.request_essentials()
        auth_url = self.auth_request(api_url=api_url, base_headers=base_headers)
        print(auth_url)

        return {
            'type': 'ir.actions.act_url',
            'url': auth_url.get("url"),
            'target': 'self'
        }

    def _request_application_details(self, api_url, base_headers):
        # Requesting application details
        if not base_headers:
            api_url, private_key, application_id, base_headers = self.request_essentials()
        application_resp = requests.get(f"{api_url}/application", headers=base_headers).json()
        return application_resp

    def auth_request(self, app=None, api_url=None, base_headers=None):
        if not app:
            app = self._request_application_details(api_url, base_headers)
        company_country_code = self.env.user.country_id.code
        body = {
            "access": {
                "valid_until": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
            },
            "aspsp": {"name": self.bank_id.name, "country": "FI"},
            "state": str(uuid.uuid4()),
            "redirect_url": app.get("redirect_urls")[0],
            "psu_type": "personal",
        }
        auth_resp = requests.post(f"{api_url}/auth", json=body, headers=base_headers).json()
        return auth_resp


class EnableBanking(models.TransientModel):
    _name = "enable.banking.wizard"
    _description = "Enable Banking Wizard"
    _rec_name = 'code'

    journal_id = fields.Many2one("account.journal", string="Journal")
    auth_url = fields.Char(string="Auth URL")
    code = fields.Char(string="Code")
    session_id = fields.Char(string="Session ID")
    account_number = fields.Char(string="Account Number", related="journal_id.bank_account_id.acc_number")
    date_from = fields.Date(string="From", default=fields.Date.today)
    date_to = fields.Date(string="To", default=fields.Date.today)

    def proceed(self):
        if not self.journal_id:
            raise ValidationError(_("Select a Journal!"))
        self._retrieve_account_transactions()

    def _create_session(self, api_url, base_headers):
        session = requests.post(f"{api_url}/sessions", json={"code": self.code}, headers=base_headers)
        if session.status_code == 200:
            # print(session.json())
            return session.json()
        else:
            print(f"Error response {session.status_code}:", session.text)
            raise ValidationError("There is a problem creating session.")

    def _get_session(self, api_url, base_headers):
        session = requests.get(f"{api_url}/sessions/{self.session_id}", headers=base_headers)
        if session.status_code == 200:
            return session.json()
        else:
            print(f"Error response {session.status_code}:", session.text)
            return

    # def _retrieve_account_balances(self):
    #     api_url, private_key, application_id, base_headers = self.journal_id.request_essentials()
    #
    #     if self.session_id:
    #         session = self._get_session(api_url, base_headers)
    #     else:
    #         session = self._create_session(api_url, base_headers)
    #         self.sudo().write({'session_id': session.get('session_id')})
    #
    #     account_uid = session["accounts"][0]["uid"]
    #     account_balance = requests.get(f"{api_url}/accounts/{account_uid}/balances", headers=base_headers)
    #     if account_balance.status_code == 200:
    #         pprint(account_balance.json())
    #     else:
    #         print(f"Error response {account_balance.status_code}:", account_balance.text)
    #         return False

    def _retrieve_account_transactions(self):
        api_url, private_key, application_id, base_headers = self.journal_id.request_essentials()

        session = self._create_session(api_url, base_headers)
        self.sudo().write({'session_id': session.get('session_id')})

        account_uid = list(filter(
            lambda x: x.get('account_id')['iban'] == self.account_number, session.get('accounts')
        ))

        query = {
            "date_from": self.date_from,
            "date_to": self.date_to
        }
        continuation_key = None
        while True:
            if continuation_key:
                query["continuation_key"] = continuation_key
            account_transaction = requests.get(
                f"{api_url}/accounts/{account_uid[0].get('uid')}/transactions",
                params=query,
                headers=base_headers,
            )
            if account_transaction.status_code == 200:
                resp_data = account_transaction.json()
                # print("Transactions:")
                pprint(resp_data["transactions"])
                continuation_key = resp_data.get("continuation_key")
                if not continuation_key:
                    print("No continuation key. All transactions were fetched")
                    break
                print(f"Going to fetch more transactions with continuation key {continuation_key}")
            else:
                print(f"Error response {account_transaction.status_code}:", account_transaction.text)
                raise ValidationError("There is a problem fetching account transaction.")

