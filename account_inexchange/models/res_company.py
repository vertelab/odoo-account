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
    invoice_inexchange = fields.Boolean(string = "Send to Inexchange", default=True)

class res_company(models.Model):
    _inherit = ['res.company','mail.thread','mail.activity.mixin']
    _name= 'res.company'
    
    inexchange_apikey = fields.Char(string='API Key',help="You get this code from your inexchange Account when tou activate Odoo",store=True)
    inexchange_client_token = fields.Char(string='Client Token',help="You get this code from your Odoo representative",store=True)
    
    
    
    @api.multi
    def inexchange_request_client_token(self):  
        # ~ self.ensure_one()
        if not self.inexchange_client_token:
            if not self.inexchange_apikey:
                raise Warning("You have to set up API Key for Inexchange, you get that when you activate Odoo in your inexchange-account")
            try:
                _logger.warn('Apikey %s Haze' % self.inexchange_apikey)
                url = "https://testapi.inexchange.com/v1/api/clientTokens/create HTTP/1.1"
                r = self.env.user.company_id.inexchange_request('POST', url,
                data={
                "erpId": self.env.user.company_id.id,
                "validTo": None ,
                })
                r = json.loads(r)
                self.inexchange_client_token = r["token"] 
                # ~ raise Warning('%s' %r.headers)
                _logger.warn('Response HTTP Haze Status Code : {status_code}'.format(status_code=r.status_code))
                _logger.warn('Response HTTP Haze Response Body : {content}'.format(content=r.content))
                auth_rec = eval(r.content)
                self.inexchange_access_token = auth_rec.get('APIKey',{}).get('AccessToken')
                _logger.warn('ClientToken %s Haze' % self.inexchange_client_token)
                self.message_post(body=_("New Client Token %s" %self.inexchange_client_token), subject=None, message_type='notification')
            except requests.exceptions.RequestException as e:
                raise Warning('HTTP Request failed %s' % e)
        else:
            
            raise Warning('Client Token already fetched')
            
            
    def company_check_status(self):
        for partner in self:
            url = "https://testapi.inexchange.com/v1/api/companies/status/ HTTP/1.1"
            r = self.env.user.company_id.inexchange_request('GET', url,
                headers={
                ClientToken: self.inexchange_client_token,
                Host: testapi.inexchange.se,
                Connection: close,
                Accept: "*/*",
                })
            self.company_id.ref = r["companyId"] 
            
    def get_company_details(self):
        self.env.user.company_id.inexchange_request_client_token()
        for partner in self:
            url = "https://v1/api/companies/details/%s" %partner.company_id.ref
            r = self.env.user.company_id.inexchange_request('GET', url,
                headers={
                ClientToken: self.inexchange_client_token,
                Host: testapi.inexchange.se,
                Accept: "*/*",
                })
    @api.multi
    def inexchange_request(self,request_type,url,data=None):
        # Company (POST /v1/api/companies/register/ HTTP/1.1)
        headers = {
            "APIKey": self.env.user.company_id.inexchange_apikey,
            "ClientToken": self.env.user.company_id.inexchange_client_token if self.env.user.company_id.inexchange_client_token else None,
            "Content-Type": "application/json",
            "Host": "testapi.inexchange.se,"
            "Content-Length": 265,
            "Expect": "100-continue",
        }
        _logger.warn('%s Haze Request_type' %request_type)
        _logger.warn('%s Haze Headers' %headers)
        _logger.warn('%s %s Haze Url DATA' %(url, data) )

        try:
            if request_type == 'POST':
                r = requests.post(url=url,headers = headers,data = json.dumps(data))
            if request_type == 'put':
                r = requests.put(url=url,headers = headers,data = json.dumps(data))
            if request_type == 'GET':
                r = requests.get(url=url,headers = headers,data = json.dumps(data))
            if request_type == 'delete':
                r = requests.delete(url=url,headers = headers)
            _logger.warn('Response HTTP Status Code : {status_code}'.format(status_code=r.status_code))
            _logger.warn('Response HTTP Response Body : {content}'.format(content=r.content))

            # ~ raise Warning(r.content)
            
            if r.status_code in [403]:
                raise Warning(r.content)
            
        except requests.exceptions.RequestException as e:
            _logger.warn('HTTP Request failed %s' % e)
            raise Warning('HTTP Request failed %s' % e)
        _logger.warn('%s Haze Content' % r.content) 
        return r.content
        
    def company_setup_request(self):
        self.env.user.company_id.inexchange_request_client_token()
        for partner in self:
            url = "https://v1/api/network/setup"
            r = self.env.user.company_id.inexchange_request('POST', url,
                headers = {
                    Host: testapi.inexchange.se,
                    Content-Type: application/json,
                    ClientToken: self.inexchange_client_token,
                    Accept: "*/*",
                    Content-Length: 152,
                },
                data = {
                    "operator": {
                      "name": "Operator Demo"
                    },
                    "name":  partner.commercial_partner_id.name,
                    "OrgNo": partner.commercial_partner_id.company_registry,
                    "GLN": partner.id_number.name,
                    "Email": partner.email,
                    "processes": [
                      "ReceiveInvoices"
                    ]
                })
            r = json.loads(r)
            
        


