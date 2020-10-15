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

class res_company(models.Model):
    _inherit = ['res.company','mail.thread', 'mail.activity.mixin']
    _name= 'res.company'
    
    fortnox_authorization_code = fields.Char(string='Authorization code',help="You get this code from your FortNox Account when tou activate Odoo")
    fortnox_client_secret = fields.Char(string='Client Secret',help="You get this code from your Odoo representative")
    fortnox_access_token = fields.Char(string='Access Token',help="With autorization code and client secret you generate this code ones")
    
    
    @api.multi
    def fortnox_get_access_token(self):  
        
        if not self.fortnox_access_token:
            if not self.fortnox_authorization_code:
                raise Warning("You have to set up Authorization_token for FortNox, you get that when you activate Odoo in your FortNox-account")
            if not self.fortnox_client_secret:
                raise Warning("You have to set up Client_secret for FortNox, you get that when you activate Odoo in your FortNox-account")
            try:
                _logger.warn('Authorization-code %s Client Secret %s' % (self.fortnox_authorization_code,self.fortnox_client_secret))

                r = requests.post(
                    url="https://api.fortnox.se/3/customers",  
                    headers = {
                        "Authorization-Code": self.fortnox_authorization_code,
                        "Client-Secret": self.fortnox_client_secret,
                        "Content-Type":"application/json",
                        "Accept":"application/json",
                    },
                )
                _logger.warn('Response HTTP Status Code : {status_code}'.format(status_code=r.status_code))
                _logger.warn('Response HTTP Response Body : {content}'.format(content=r.content))
                auth_rec = eval(r.content)
                self.fortnox_access_token = auth_rec.get('Authorization',{}).get('AccessToken')
                self.message_post(body=_("New Access Token %s" %self.fortnox_access_token), subject=None, message_type='notification')
            except requests.exceptions.RequestException as e:
                raise Warning('HTTP Request failed %s' % e)
        else:
            
            raise Warning('Access Token already fetched')
            
            
    
    @api.multi
    def fortnox_request(self,request_type,url,data=None):
        # Customer (POST https://api.fortnox.se/3/customers)
        headers = {
            "Access-Token": self.fortnox_access_token,
            "Client-Secret": self.fortnox_client_secret,
            "Content-Type":"application/json",
            "Accept":"application/json",
        }

        try:
            if request_type == 'post':
                r = requests.post(url=url,headers = headers,data = json.dumps(data))
            if request_type == 'put':
                r = requests.put(url=url,headers = headers,data = json.dumps(data))
            if request_type == 'get':
                r = requests.get(url=url,headers = headers)
            if request_type == 'delete':
                r = requests.get(url=url,headers = headers)
            _logger.warn('Response HTTP Status Code : {status_code}'.format(status_code=r.status_code))
            _logger.warn('Response HTTP Response Body : {content}'.format(content=r.content))

            # ~ raise Warning(r.content)
            
            if r.status_code in [403]:
                raise Warning(r.content)
            
        except requests.exceptions.RequestException as e:
            _logger.warn('HTTP Request failed %s' % e)
            raise Warning('HTTP Request failed %s' % e)
        return r.content

