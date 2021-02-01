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

import json
import logging
import requests

from odoo import models, fields, api
from odoo.exceptions import Warning

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    attachment_ids = fields.Many2many(
        'ir.attachment', 'class_id', 'attachment_id', 'Attachments')
    inexchange_apikey = fields.Char(
        string='API Key', config_parameter='inexchange.apikey',
        help="You get this code from your inexchange Account when you "
             "activate Odoo",
        store=True)
    inexchange_client_token = fields.Char(
        string='Client Token', config_parameter='inexchange.client.token',
        help="You get this code from your Odoo representative",
        store=True)
    invoice_inexchange = fields.Boolean(
        string="Send to Inexchange", default=True)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()

    @api.model
    def get_url(self, endpoint):
        base_url = 'https://testapi.inexchange.se/v1/api'
        return f'{base_url}/{endpoint.lstrip("/")}'

    # ~ @api.multi
    def inexchange_request_client_token(self):
        client_token = self.env['ir.config_parameter'].sudo().get_param(
            'inexchange.client.token')
        if not client_token:
            api_key = self.env['ir.config_parameter'].sudo().get_param(
                'inexchange.apikey')
            if not api_key:
                raise Warning("You have to set up API Key for Inexchange"
                              ", you get that when you activate Odoo in "
                              "your inexchange-account")
            try:
                url = "https://testapi.inexchange.se/v1/api/clientTokens/create"
                r = self.env['res.config.settings'].inexchange_request_api(
                    'POST', url, data={
                        "erpId": self.env.user.company_id.id,
                        "validTo": None},)
                r = json.loads(r)
                client_token = r["token"]
                self.env['ir.config_parameter'].sudo().set_param(
                    'inexchange.client.token', client_token)
            except requests.exceptions.RequestException as e:
                raise Warning('HTTP Request failed %s' % e)
        return client_token

    @api.multi
    def inexchange_request_api(self,request_type,url,data=None):
        # Company (POST /v1/api/companies/register/ HTTP/1.1)
        api_key = self.env['ir.config_parameter'].sudo().get_param(
            'inexchange.apikey')
        headers = {
                    "APIKey": api_key,
                    "Content-Type": "application/json; charset=utf-8",
                    "Host": "testapi.inexchange.se",
                    "Content-Length": str(len(data)) if data else None,
                    "Expect": "100-continue",
                }
        try:
            if request_type == 'POST':
                r = requests.post(
                    url=url, headers=headers, data=json.dumps(data),verify=False)
            _logger.warn(f'Response HTTP Status Code : {r.status_code}')
            _logger.warn(f'Response HTTP Response Body : {r.content}')

            if r.status_code in [403]:
                raise Warning(r.content)

        except requests.exceptions.RequestException as e:
            _logger.warn('HTTP Request failed %s' % e)
            raise Warning('HTTP Request failed %s' % e)
        _logger.warn('%s Haze Content 1 ' % r.content) 
        return r.content

    @api.multi
    def inexchange_request_token(self, request_type, url, data=None):
        # Company (POST /v1/api/companies/register/ HTTP/1.1)
        client_token = self.env['res.config.settings'].inexchange_request_client_token()
        headers = {
                    "ClientToken": client_token,
                    "Host": "testapi.inexchange.se",
                    "Content-Type": "application/json",
                    "Accept": "*/*",
                    "Content-Length": str(len(data)) if data else None,
                }

        try:
            if request_type == 'POST':
                r = requests.post(url = url,headers = headers,data = json.dumps(data),verify=False)
            if request_type == 'GET':
                r = requests.get(url = url,headers = headers,data = json.dumps(data),verify=False)
            _logger.warn('Response HTTP Status Code : {status_code}'.format(status_code=r.status_code))
            _logger.warn('Response HTTP Response Body : {content}'.format(content=r.content))

            if r.status_code in [403]:
                raise Warning(r.content)

        except requests.exceptions.RequestException as e:
            _logger.warn('HTTP Request failed %s' % e)
            raise Warning('HTTP Request failed %s' % e)
        return r.content
