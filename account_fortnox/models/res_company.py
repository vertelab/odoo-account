# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2020 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import base64
import json
import logging
from datetime import datetime, timedelta

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Fortnox API constants
FORTNOX_TOKEN_URL = "https://apps.fortnox.se/oauth-v1/token"
TOKEN_LIFETIME_MINUTES = 59


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_fortnox = fields.Boolean(string="Send to Fortnox", default=True)


class ResCompany(models.Model):
    _inherit = ['res.company', 'mail.thread', 'mail.activity.mixin']
    _name = 'res.company'

    fortnox_authorization_code = fields.Char(
        string='Authorization code',
        help="You get this code from your FortNox Account when you activate Odoo",
        store=True
    )
    fortnox_client_secret = fields.Char(
        string='Client Secret',
        help="You get this code from your Odoo representative",
        store=True
    )
    fortnox_access_token = fields.Text(
        string='Access Token',
        help="With authorization code and client secret you generate this code once",
        store=True
    )
    fortnox_client_id = fields.Char(
        string='Client ID',
        help="The public ID of the integration",
        store=True
    )
    fortnox_token_expiration = fields.Datetime(
        "When the token expires",
        store=True
    )
    fortnox_refresh_token = fields.Text(store=True)

    def fortnox_get_access_token(self):
        """Get initial access token using authorization code."""
        if self.fortnox_access_token:
            raise UserError('Access Token already fetched')

        self._validate_fortnox_credentials()

        try:
            base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
            redirect_uri = f"{base_url}/fortnox/auth"

            auth_response = self._request_fortnox_token(
                grant_type='authorization_code',
                code=self.fortnox_authorization_code,
                redirect_uri=redirect_uri
            )

            self._update_tokens_from_response(auth_response)
            _logger.info(f"Successfully obtained access token for company {self.id}")

        except requests.exceptions.RequestException as e:
            _logger.exception(f"Failed to get access token: {e}")
            raise UserError(f'HTTP Request failed: {e}')

    def fortnox_refresh_access_token(self):
        """Refresh expired access token using refresh token."""
        if not self.fortnox_refresh_token:
            raise UserError('Refresh token is missing')

        try:
            auth_response = self._request_fortnox_token(
                grant_type='refresh_token',
                refresh_token=self.fortnox_refresh_token
            )

            self._update_tokens_from_response(auth_response)
            _logger.info(f"Successfully refreshed access token for company {self.id}")

        except requests.exceptions.RequestException as e:
            _logger.exception(f"Failed to refresh access token: {e}")
            raise UserError(f'HTTP Request failed: {e}')

    def is_access_token_expired(self):
        """Check if access token is expired or missing."""
        if not self.fortnox_access_token or not self.fortnox_token_expiration:
            return True
        return datetime.now() >= self.fortnox_token_expiration

    def fortnox_request(self, request_type, url, data=None, files=None, raise_error=True):
        """Make authenticated request to Fortnox API with automatic token refresh."""
        self._ensure_valid_token()

        headers = self._build_request_headers(files)

        _logger.debug(f"Fortnox request: {request_type} {url}")

        try:
            if files:
                response = requests.request(request_type, url=url, headers=headers, files=files)
            else:
                response = requests.request(request_type, url=url, headers=headers, data=json.dumps(data))

            if raise_error and response.status_code not in (200, 201, 204):
                _logger.error(f"Fortnox API error: {response.status_code} - {response.content}")
                raise UserError(f'Fortnox API error: {response.status_code}\n{response.content}')

            return response.json()

        except requests.exceptions.RequestException as e:
            _logger.exception(f"Request to Fortnox failed: {e}")
            if raise_error:
                raise UserError(f'HTTP Request failed: {e}')
            return {}

    def fortnox_auth_open_link(self):
        """Open Fortnox authorization link in new window."""
        return {
            'type': 'ir.actions.act_url',
            'url': f'/fortnox/auth?run_get=True&state={self.id}',
            'target': 'new',
        }

    # Private helper methods

    def _validate_fortnox_credentials(self):
        """Validate that all required Fortnox credentials are present."""
        if not self.fortnox_authorization_code:
            raise UserError(
                "You have to set up Authorization code for Fortnox. "
                "You get that when you activate Odoo in your Fortnox account."
            )
        if not self.fortnox_client_secret:
            raise UserError(
                "You have to set up Client Secret for Fortnox. "
                "You get that when you activate Odoo in your Fortnox account."
            )
        if not self.fortnox_client_id:
            raise UserError("You have to supply the client ID of the integration")

    def _get_basic_auth_header(self):
        """Generate Basic Authentication header for Fortnox token requests."""
        credentials = f"{self.fortnox_client_id}:{self.fortnox_client_secret}"
        credentials_encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        return f"Basic {credentials_encoded}"

    def _request_fortnox_token(self, grant_type, code=None, refresh_token=None, redirect_uri=None):
        """Make token request to Fortnox OAuth endpoint."""
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": self._get_basic_auth_header(),
        }

        data = {'grant_type': grant_type}

        if grant_type == 'authorization_code':
            data['code'] = code
            data['redirect_uri'] = redirect_uri
        elif grant_type == 'refresh_token':
            data['refresh_token'] = refresh_token

        response = requests.post(url=FORTNOX_TOKEN_URL, headers=headers, data=data)

        if response.status_code not in (200, 201, 204):
            raise UserError(
                f'Fortnox token request failed\n'
                f'Status: {response.status_code}\n'
                f'Content: {response.content}'
            )

        return json.loads(response.content)

    def _update_tokens_from_response(self, auth_response):
        """Update company tokens from Fortnox authentication response."""
        self.fortnox_access_token = auth_response.get('access_token')
        self.fortnox_refresh_token = auth_response.get('refresh_token')
        self.fortnox_token_expiration = datetime.now() + timedelta(minutes=TOKEN_LIFETIME_MINUTES)

    def _ensure_valid_token(self):
        """Ensure access token is valid, refreshing if necessary."""
        if not self.fortnox_access_token:
            _logger.info("Access token not fetched, fetching now")
            self.fortnox_get_access_token()
            self.env.cr.commit()
        elif self.is_access_token_expired():
            _logger.info("Access token expired, refreshing")
            self.fortnox_refresh_access_token()
            self.env.cr.commit()

    def _build_request_headers(self, files=None):
        """Build request headers for Fortnox API calls."""
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.fortnox_access_token}"
        }

        # Only set Content-Type if not sending files
        if not files:
            headers["Content-Type"] = "application/json"

        return headers