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

from odoo import models, fields, api, _
import time
import re
from odoo.exceptions import except_orm, Warning, RedirectWarning
import requests
import json
import logging
_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    inexchange_apikey = fields.Char(string='API Key',config_parameter='inexchange.apikey',help="You get this code from your inexchange Account when tou activate Odoo",store=True)
    inexchange_client_token = fields.Char(string='Client Token',config_parameter='inexchange.client.token',help="You get this code from your Odoo representative",store=True)
    invoice_inexchange = fields.Boolean(string = "Send to Inexchange", default=True)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
    
    @api.multi
    def inexchange_request_client_token(self):  
        client_token = self.env['ir.config_parameter'].sudo().get_param('inexchange.client.token')
        if not client_token:
            api_key = self.env['ir.config_parameter'].sudo().get_param('inexchange.apikey')
            if not api_key:
                raise Warning("You have to set up API Key for Inexchange, you get that when you activate Odoo in your inexchange-account")
            try:
                _logger.warn('Apikey %s Haze' % api_key)
                r = requests.post( 
                url = "https://testapi.inexchange.se/v1/api/clientTokens/create",
                headers = {
                    "APIKey": api_key,
                    "Content-Type": "application/json; charset=utf-8",
                    "Host": "testapi.inexchange.se",
                    "Content-Length": "183",
                    "Expect": "100-continue",
                },
                data={
                "erpId": self.env['res.company'].partner_id.id,
                "validTo": None ,
                },)
                _logger.warn('Response HTTP Haze Status Code : {status_code}'.format(status_code=r.status_code))
                _logger.warn('Response HTTP Haze Response Body : {content}'.format(content=r.content))
                auth_rec = eval(r.content)
                client_token = auth_rec.get('APIKey',{}).get('APIKey')
                _logger.warn('ClientToken %s Haze' % self.inexchange_client_token)
                self.env['ir.config_parameter'].sudo().set_param('inexchange.client.token',client_token)
            except requests.exceptions.RequestException as e:
                raise Warning('HTTP Request failed %s' % e)
        else:
            
            raise Warning('Client Token already fetched')
            
            
            
    
    # ~ @api.multi
    # ~ def inexchange_request(self,request_type,url,data=None):
        # ~ # Company (POST /v1/api/companies/register/ HTTP/1.1)
        # ~ api_key = self.env['ir.config_parameter'].sudo().get_param('inexchange.apikey')
        # ~ _logger.warn('%s Haze Request_type' %request_type)
        # ~ _logger.warn('%s Haze Headers' %headers)
        # ~ _logger.warn('%s %s Haze Url DATA' %(url, data) )

        # ~ try:
            # ~ if request_type == 'POST':
                # ~ r = requests.post(url=url,data = json.dumps(data))
            # ~ if request_type == 'GET':
                # ~ r = requests.get(url=url,data = json.dumps(data))
            # ~ _logger.warn('Response HTTP Status Code : {status_code}'.format(status_code=r.status_code))
            # ~ _logger.warn('Response HTTP Response Body : {content}'.format(content=r.content))

            # ~ raise Warning(r.content)
            
            # ~ if r.status_code in [403]:
                # ~ raise Warning(r.content)
            
        # ~ except requests.exceptions.RequestException as e:
            # ~ _logger.warn('HTTP Request failed %s' % e)
            # ~ raise Warning('HTTP Request failed %s' % e)
        # ~ _logger.warn('%s Haze Content' % r.content) 
        # ~ return r.content
        
        
        
            
        


