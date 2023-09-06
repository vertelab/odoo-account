from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timezone, timedelta
import jwt as pyjwt
import requests
from pprint import pprint
from urllib.parse import urlparse, parse_qs
import werkzeug
import uuid


class ResConfigSettings(models.Model):
    _inherit = 'res.company'

    enable_banking_api_url = fields.Char("API URL")

    enable_banking_application_id = fields.Char("Application ID")

    enable_banking_redirect_url = fields.Char("Redirect URL")

    enable_banking_private_key = fields.Text("Private Key")

    def enable_baking_settings(self):
        pass

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