from odoo import models, fields, api, _
from datetime import datetime, timezone, timedelta
import jwt as pyjwt
import requests
import uuid
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.Model):
    _inherit = 'res.partner'

    enable_banking_api_url = fields.Char("API URL")

    enable_banking_application_id = fields.Char("Application ID")

    enable_banking_redirect_url = fields.Char("Redirect URL")

    enable_banking_private_key = fields.Text("Private Key")

    def request_essentials(self):
        api_url = self.enable_banking_api_url
        private_key = self.enable_banking_private_key
        application_id = self.enable_banking_application_id

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
        try:
            base_headers = {"Authorization": f"Bearer {jwt.decode('utf-8')}"}
        except AttributeError:
            base_headers = {"Authorization": f"Bearer {jwt}"}
        return api_url, private_key, application_id, base_headers

    def action_sync_transactions_with_enable_banking(self, bank_id):
        api_url, private_key, application_id, base_headers = self.request_essentials()
        auth_url = self.auth_request(bank_id, api_url=api_url, base_headers=base_headers)
        return auth_url

    def _request_application_details(self, api_url, base_headers):
        # Requesting application details
        if not base_headers:
            api_url, private_key, application_id, base_headers = self.request_essentials()
        application_resp = requests.get(f"{api_url}/application", headers=base_headers).json()
        return application_resp

    def auth_request(self, bank_id=None, app=None, api_url=None, base_headers=None):
        _logger.warning(f"{bank_id.name=} {bank_id.country.code=}")
        if not app:
            app = self._request_application_details(api_url, base_headers)
        #_logger.warning({f"{app=}"})
        body = {
            "access": {
                "valid_until": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
            },
            "aspsp": {"name": bank_id.name, "country": bank_id.country.code},
            "state": str(uuid.uuid4()),
            "redirect_url": app.get("redirect_urls")[0],
            "psu_type": "business",
            # "psu_type": "personal",
        }
        auth_resp = requests.post(f"{api_url}/auth", json=body, headers=base_headers).json()
        return auth_resp
