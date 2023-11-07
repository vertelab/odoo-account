# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import except_orm, Warning, RedirectWarning
import requests
import json

import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fortnox_authorization_code = fields.Char('Authorization code', config_parameter='fortnox.authorization.code',
                                             help="You get this code from your FortNox Account when tou activate Odoo")
    fortnox_client_secret = fields.Char('Client Secret', config_parameter='fortnox.client.secret',
                                        help="You get this code from your Odoo representative")
    fortnox_access_token = fields.Char('Access Token', config_parameter='fortnox.access.token',
                                       help="With authorization code and client secret you generate this code ones")

    # ~ invoice_fortnox = fields.Boolean(string = "Send to Fortnox", default=True)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()

    @api.multi
    def fortnox_get_access_token(self):
        Access_token = self.env['ir.config_parameter'].sudo().get_param('fortnox.access.token')
        if not Access_token:
            Authorization_code = self.env['ir.config_parameter'].sudo().get_param('fortnox.authorization.code')
            if not Authorization_code:
                raise Warning(
                    "You have to set up Authorization_token for FortNox, you get that when you activate Odoo in your "
                    "FortNox-account")
            Client_secret = self.env['ir.config_parameter'].sudo().get_param('fortnox.client.secret')
            if not Client_secret:
                raise Warning(
                    "You have to set up Client_secret for FortNox, you get that when you activate Odoo in your "
                    "FortNox-account")
            try:
                _logger.warning('Authorization-code %s Client Secret %s' % (Authorization_code, Client_secret))

                r = requests.post(
                    url="https://api.fortnox.se/3/customers",
                    headers={
                        "Authorization-Code": Authorization_code,
                        "Client-Secret": Client_secret,
                        "Content-Type": "application/json",
                        "Accept": "application/json"},
                )
                _logger.warning('Response HTTP Status Code : {status_code}'.format(status_code=r.status_code))
                _logger.warning('Response HTTP Response Body : {content}'.format(content=r.content))
                auth_rec = eval(r.content)
                Access_token = auth_rec.get('Authorization', {}).get('AccessToken')
                self.env['ir.config_parameter'].sudo().set_param('fortnox.access.token', Access_token)
            except requests.exceptions.RequestException as e:
                _logger.warning('HTTP Request failed %s' % e)
        else:
            _logger.warning('Access Token already fetched')

    @api.model
    def fortnox_request(self, request_type, url, data=None, raise_error=True):
        # Customer (POST https://api.fortnox.se/3/customers)
        Access_token = self.env['ir.config_parameter'].sudo().get_param('fortnox.access.token')
        Client_secret = self.env['ir.config_parameter'].sudo().get_param('fortnox.client.secret')
        headers = {
            "Access-Token": Access_token,
            "Client-Secret": Client_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            if request_type == 'post':
                r = requests.post(
                    url=url, headers=headers, data=json.dumps(data))
            if request_type == 'put':
                r = requests.put(
                    url=url, headers=headers, data=json.dumps(data))
            if request_type == 'get':
                r = requests.get(url=url, headers=headers)
            if request_type == 'delete':
                r = requests.get(url=url, headers=headers)
            _logger.warning(f'Response HTTP Status Code : {r.status_code}')
            _logger.warning(f'Response HTTP Response Body : {r.content}')

            # ~ raise Warning(r.content)

            if raise_error and r.status_code in [403]:
                raise Warning(r.content)

        except requests.exceptions.RequestException as e:
            _logger.warning('HTTP Request failed %s' % e)
            raise Warning('HTTP Request failed %s' % e)
        return r.content
