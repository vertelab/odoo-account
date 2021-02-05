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
from odoo import http
import json
import logging
import requests

_logger = logging.getLogger(__name__)

class res_company(models.Model):
    _inherit = ['res.company','mail.thread','mail.activity.mixin']
    _name= 'res.company'

    @api.multi
    def register_company(self):
        try:
            for company in self:
                if not company.partner_id.ref:
                    url = "https://testapi.inexchange.se/v1/api/companies/register"
                    """ r = response """
                    r = self.env['res.config.settings'].inexchange_request_api('POST', url,
                        data={
                        "erpId": company.partner_id.id,
                        "orgNo": company.company_registry,
                        "vatNo": company.vat,
                        "name": company.name,
                        "erpProduct": "DEMO Product 1.0",
                        "city": company.city,
                        "countryCode": "SE",
                        "languageCode": "sv-SE",
                        "email": company.email,
                        "isVatRegistered": True,
                        "processes": [
                            "SendInvoices",
                            "ReceiveInvoices",
                        ]})
                    r = json.loads(r)
                    _logger.warn('%s Haze Company' % r)
                
                # ~ company.update_company_info()
                company.company_check_status()
                # ~ company.get_company_details()

        except requests.exceptions.RequestException as e:
            _logger.warn('HTTP Request failed %s' % e)
            raise Warning('HTTP Request failed %s' % e)

        # ~ return r  

    @api.multi
    def update_company_info(self):
        for company in self:
            url = "https://testapi.inexchange.se/v1/api/companies/register"
            """ r = response """
            r = self.env['res.config.settings'].inexchange_request_api('POST', url,
                data={
                "erpId": company.partner_id.id,
                "orgNo": company.company_registry,
                "vatNo": company.vat,
                "name": company.name,
                "erpProduct": "DEMO Product 1.0",
                "city": company.city,
                "countryCode": "SE",
                "languageCode": "sv-SE",
                "email": company.email,
                "isVatRegistered": True,
                "processes": [
                    "SendInvoices",
                    "ReceiveInvoices",
                ]})
            r = json.loads(r)
            _logger.warn('%s Haze Update' % r)
            # ~ raise Warning(r.content)
        company.company_check_status()
        # ~ return r  

    @api.multi
    def company_check_status(self):
        url = "https://testapi.inexchange.se/v1/api/companies/status"
        for company in self:
            r = self.env['res.config.settings'].inexchange_request_token('GET', url)
            r = json.loads(r)
            company.partner_id.ref = r["companyId"]
            _logger.warn('Haze company ID %s' % company.partner_id.ref)

    @api.multi
    def get_company_details(self):
        self.env['res.config.settings'].inexchange_request_client_token()
        for company in self:
            url = "https://testapi.inexchange.se/v1/api/companies/details/%s" %company.partner_id.ref
            r = self.env['res.config.settings'].inexchange_request_token('GET', url)
            _logger.warn('Haze company details %s' %r)

    @api.multi
    def company_setup_request(self):
        self.env['res.config.settings'].inexchange_request_client_token()
        url = "https://testapi.inexchange.se/v1/api/network/setup"
        for company in self:
            
            r = self.env['res.config.settings'].inexchange_request_token('POST', url,
                data = {
                    "operator": {
                      "name": "Operator Demo"
                    },
                    "name":  company.name,
                    "OrgNo": company.company_registry,
                    "GLN": company.partner_id.commercial_partner_id.gln_number_vertel,
                    "Email": company.email,
                    "processes": [
                      "ReceiveInvoices"
                    ]
                })
            r = json.loads(r)

    @api.multi
    def add_identifiers(self):
        self.env['res.config.settings'].inexchange_request_client_token()
        for company in self:
            url = "https://testapi.inexchange.se/v1/api/companies/identifiers"
            r = self.env['res.config.settings'].inexchange_request_token('POST',url,
                data = {
                    "operator": {
                      "name": "Operator Demo"
                    },
                    "name":  company.name,
                    "OrgNo": company.company_registry,
                    "GLN": company.partner_id.commercial_partner_id.gln_number_vertel,
                    "Email": company.email,
                    "processes": [
                      "ReceiveInvoices"
                    ]
                })
            r = json.loads(r)

    @api.multi
    def add_users(self):
        self.env['res.config.settings'].inexchange_request_client_token()
        for company in self:
            url = "https://testapi.inexchange.se/v1/api/companies/identifiers"
            r = self.env['res.config.settings'].inexchange_request_token('POST', url,
                data = {
                    "operator": {
                      "name": "Operator Demo"
                    },
                    "name":  company.name,
                    "OrgNo": company.company_registry,
                    "GLN": company.partner_id.commercial_partner_id.gln_number_vertel,
                    "Email": company.email,
                    "processes": [
                      "ReceiveInvoices"
                    ]
                })
            r = json.loads(r)

class res_partner(models.Model):
    _inherit = 'res.partner'

    gln_number_vertel = fields.Char(string = "GLN Number", help = "This is for GLN Number")
    inexchange_company_id = fields.Char(string = "Inexchange Company ID", help = "This is for Inexchange Company ID")
    company_org_number = fields.Char(string = "Company Registry", help = "Company Registry")

    def merge_gln_number(self):
        for contact in self.env['res.partner'].search([]):
            if contact.gln_number:
                contact.gln_number_vertel = contact.gln_number
                
    def merge_org_number(self):
        for contact in self.env['res.partner'].search([]):
            if contact.org_no:
                contact.company_org_number = contact.org_no
    
    @api.one
    def lookup_buyer_company(self):
        settings = self.env['res.config.settings']
        url = settings.get_url(endpoint='buyerparties/lookup')
        client_token = settings.inexchange_request_client_token()
        if self.commercial_partner_id.gln_number_vertel:
            header = {
                'Content-Type': 'application/json',
                'ClientToken': client_token,
                
            }
            data = {
                'PartyId': self.commercial_partner_id.company_org_number or False,
                'Name': self.commercial_partner_id.name if not self.commercial_partner_id.parent_id else self.commercial_partner_id.parent_id.name,
            }
            # ~ _logger.info('Haze %s' %json.dumps(data))
            result = requests.post(url, headers=header, data=json.dumps(data))
            result_party = json.loads(result.text)['parties']
            for entry in result_party:
                if entry.get('receiveElectronicInvoiceCapability') =='ReceivingElectronicInvoices':
                    if entry.get('gln') == self.commercial_partner_id.gln_number_vertel:
                        self.commercial_partner_id.inexchange_company_id = entry["companyId"]
                    
            
            if not self.inexchange_company_id:
                raise Warning('%s is not in Inexchange' % self.commercial_partner_id.name)
            # ~ _logger.info('Haze %s' %json.loads(result.text))
            if result.status_code not in (200,):
                raise Warning('Failed to check partner')
        else:
            raise Warning('%s has no gln number' %self.commercial_partner_id.name)
        

