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
import binascii
import os
import time
import re
import base64
from odoo.exceptions import except_orm, Warning, RedirectWarning
import requests
from odoo import http
import json
import logging
from odoo.http import content_disposition, dispatch_rpc, request, \
    serialize_exception as _serialize_exception, Response
_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    attachment_ids = fields.Many2many('ir.attachment', 'class_id', 'attachment_id', 'Attachments')
    inexchange_apikey = fields.Char(string='API Key',config_parameter='inexchange.apikey',help="You get this code from your inexchange Account when tou activate Odoo",store=True)
    inexchange_client_token = fields.Char(string='Client Token',config_parameter='inexchange.client.token',help="You get this code from your Odoo representative",store=True)
    invoice_inexchange = fields.Boolean(string = "Send to Inexchange", default=True)
    # ~ inexchange_test_host = fields.Char(string='Test Host',config_parameter='inexchange.test.host',help="Test Host for Inexchange",store=True)
    # ~ inexchange_real_host = fields.Char(string='Real Host',config_parameter='inexchange.real.host',help="Real Host for Inexchange",store=True)
    #TODO
    #test_host = "testapi.inexchange.se"
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
    
    # ~ @api.multi
    def inexchange_request_client_token(self):  
        client_token = self.env['ir.config_parameter'].sudo().get_param('inexchange.client.token')
        if not client_token:
            api_key = self.env['ir.config_parameter'].sudo().get_param('inexchange.apikey')
            if not api_key:
                raise Warning("You have to set up API Key for Inexchange, you get that when you activate Odoo in your inexchange-account")
            try:
                _logger.warn('Apikey %s Haze' % api_key)
                url = "https://testapi.inexchange.se/v1/api/clientTokens/create"
                r = self.env['res.config.settings'].inexchange_request_api('POST', url,
                    data={
                    "erpId": self.env.user.company_id.id,
                    "validTo": None ,
                    },)
                r = json.loads(r)
                client_token = r["token"]
                _logger.warn('ClientToken %s Haze' % client_token)
                return client_token
            except requests.exceptions.RequestException as e:
                raise Warning('HTTP Request failed %s' % e)
        
            
            
            
    
    @api.multi
    def inexchange_request_api(self,request_type,url,data=None):
        # Company (POST /v1/api/companies/register/ HTTP/1.1)
        api_key = self.env['ir.config_parameter'].sudo().get_param('inexchange.apikey')
        headers = {
                    "APIKey": api_key,
                    "Content-Type": "application/json; charset=utf-8",
                    "Host": "testapi.inexchange.se",
                    "Content-Length": str(len(data)),
                    "Expect": "100-continue",
                }
        _logger.warn('%s Haze Request_type' %request_type)
        _logger.warn('%s Haze Headers' %headers)
        _logger.warn('%s %s Haze Url DATA' %(url, data) )

        try:
            if request_type == 'POST':
                r = requests.post(url = url,headers = headers,data = json.dumps(data))
            # ~ if request_type == 'GET':
                # ~ r = requests.get(url=url,data = json.dumps(data))
            _logger.warn('Response HTTP Status Code : {status_code}'.format(status_code=r.status_code))
            _logger.warn('Response HTTP Response Body : {content}'.format(content=r.content))

            # ~ raise Warning(r.content)
            
            if r.status_code in [403]:
                raise Warning(r.content)
            
        except requests.exceptions.RequestException as e:
            _logger.warn('HTTP Request failed %s' % e)
            raise Warning('HTTP Request failed %s' % e)
        _logger.warn('%s Haze Content 1 ' % r.content) 
        return r.content
        
    @api.multi
    def inexchange_request_token(self,request_type,url,data=None):
        # Company (POST /v1/api/companies/register/ HTTP/1.1)
        client_token = self.env['res.config.settings'].inexchange_request_client_token()
        headers = {
                    "ClientToken": client_token,
                    "Host": "testapi.inexchange.se",
                    "Content-Type": "application/json",
                    "Accept": "*/*",
                    "Content-Length": str(len(data)) if data else None,
                }
        # ~ _logger.warn('%s Haze Request_type' %request_type)
        # ~ _logger.warn('%s Haze Headers' %headers)
        # ~ _logger.warn('%s %s Haze Url DATA' %(url, data) )

        try:
            if request_type == 'POST':
                r = requests.post(url = url,headers = headers,data = json.dumps(data))
            if request_type == 'GET':
                r = requests.get(url = url,headers = headers,data = json.dumps(data))
            _logger.warn('Response HTTP Status Code : {status_code}'.format(status_code=r.status_code))
            _logger.warn('Response HTTP Response Body : {content}'.format(content=r.content))

            # ~ raise Warning(r.content)
            
            if r.status_code in [403]:
                raise Warning(r.content)
            
        except requests.exceptions.RequestException as e:
            _logger.warn('HTTP Request failed %s' % e)
            raise Warning('HTTP Request failed %s' % e)
        _logger.warn('%s Haze Content 2' % r.content) 
        return r.content
    #TODO:how to find a bundary which we can send to Inexchange? Order Number? it depends on us
    @api.multi
    def inexchange_invoice_upload(self, request_type, url, data=None):
        client_token = self.env['res.config.settings'].inexchange_request_client_token()
        url = "https://testapi.inexchange.se/v1/api/documents"
        for attachment in self.attachment_ids:
            decoded_data = base64.b64decode(attachment)
            with open(attachment, 'rb') as f:
                r = requests.post(url, files={attachment: f})
            _logger.debug('Haze.text %s' %attachment)
        # ~ document_name = self.env['ir.attachment'].res_name
        # ~ _logger.warn('Hazedocument %s' %document_name)
        # ~ attachments = self.env['ir.attachment'].create({
            # ~ 'res_model':self._name,
            # ~ 'res_id': self.id,
            # ~ 'datas': base64.b64encode(data),
            # ~ }
        # ~ )
        # ~ attachment = self.env['ir.attachment'].create({
            # ~ 'res_model': self._name,
            # ~ 'res_id': self.id,
            # ~ 'datas': base64.b64encode(data),
            # ~ 'name': 'UBL-Invoice-2.1.xml',
            # ~ 'datas_fname': 'UBL-Invoice-2.1.xml',
        # ~ })
        # ~ _logger.warn('Hazeattachment %s' %attachment)
        # ~ _logger.warn('%s Hazelocation**' %client_token)
        # ~ headers = {
                    # ~ "ClientToken": client_token,
                    # ~ "Host": "testapi.inexchange.se",
                    # ~ "Accept": "*/*",
                    # ~ "Content-Type": "multipart/form-data; boundary=%s" %boundary,
                    # ~ "Content-Length": str(len(data)) if data else None,
                    # ~ "Content-Length": str(len(base64.b64encode(data))) if data else None,
                    
                    # ~ "boundary":{
                    # ~ "Content-Disposition": 'form-data; name="File"; content_disposition(name))',
                    # ~ #filename we have to set as well,
                    # ~ "Content-Type": "application/xml",
                    # ~ },
                # ~ }
        # ~ _logger.warn('%s Hazelocation*' %client_token)
        # ~ _logger.warn('%s Haze upload Request_type' %request_type)
        # ~ _logger.warn('%s Haze upload Headers' %headers)
        # ~ _logger.warn('%s %s Haze upload Url DATA' %(url, data) )
        # ~ try:
            # ~ if request_type == 'POST':
                # ~ r = requests.post(url = url,headers = headers,data = data)
                # ~ r = requests.post(url = url,headers = headers,data = base64.b64encode(data))
            # ~ _logger.warn('Response HTTP Status Code : {status_code}'.format(status_code=r.status_code))
            # ~ _logger.warn('Response HTTP Response Body : {content}'.format(content=r.content))

            # ~ raise Warning(r.content)
            
            # ~ if r.status_code in [403]:
                # ~ raise Warning(r.content)
            
        # ~ except requests.exceptions.RequestException as e:
            # ~ _logger.warn('HTTP Request failed %s' % e)
            # ~ raise Warning('HTTP Request failed %s' % e)
        # ~ _logger.warn('%s Haze upload Content 2' % r.content) 
        # ~ return r.content
        
        
        
            
        


