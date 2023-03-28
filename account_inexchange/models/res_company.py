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

    def register_company(self):
        settings = self.env['res.config.settings']
        url = settings.get_url(endpoint='companies/register')
        try:
            for company in self:
                if not company.partner_id.ref:
                    """ r = response """
                    r = settings.inexchange_request_api('POST', url,
                        data={
                        "ErpId": company.partner_id.id,
                        "OrgNo": company.company_registry,
                        "VatNo": company.vat,
                        "Name": company.name,
                        "ErpProduct": "Medical Product 1.0",
                        "City": company.city,
                        "CountryCode": "SE",
                        "LanguageCode": "sv-SE",
                        "Email": company.email,
                        "IsVatRegistered": True,
                        "Processes": [
                            "SendInvoices"
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

    def update_company_info(self):
        settings = self.env['res.config.settings']
        url = settings.get_url(endpoint='companies/register')
        for company in self:
            """ r = response """
            r = settings.inexchange_request_api('POST', url,
                data={
                "ErpId": company.partner_id.id,
                "OrgNo": company.company_registry,
                "VatNo": company.vat,
                "Name": company.name,
                "ErpProduct": "DEMO Product 1.0",
                "City": company.city,
                "CountryCode": "SE",
                "LanguageCode": "sv-SE",
                "Email": company.email,
                "IsVatRegistered": True,
                "Processes": [
                    "SendInvoices"
                ]})
            r = json.loads(r)
            _logger.warn('%s Haze Update' % r)
            # ~ raise Warning(r.content)
        company.company_check_status()
        # ~ return r  

    def company_check_status(self):
        settings = self.env['res.config.settings']
        url = settings.get_url(endpoint='companies/status')
        for company in self:
            r = settings.inexchange_request_token('GET', url)
            r = json.loads(r)
            raise Warning(str(r))
            # ~ company.partner_id.ref = r["CompanyId"]
            _logger.warn('Haze company ID %s' % company.partner_id.ref)

    def get_company_details(self):
        settings = self.env['res.config.settings']
        url = settings.get_url(endpoint='companies/details/%s' %company.partner_id.ref)
        settings.inexchange_request_client_token()
        for company in self:
            r = settings.inexchange_request_token('GET', url)
            _logger.warn('Haze company details %s' %r)

    def company_setup_request(self):
        settings = self.env['res.config.settings']
        url = settings.get_url(endpoint='network/setup')
        settings.inexchange_request_client_token()
        for company in self:
            
            r = settings.inexchange_request_token('POST', url,
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

    def add_identifiers(self):
        settings = self.env['res.config.settings']
        url = settings.get_url(endpoint='companies/identifiers')
        settings.inexchange_request_client_token()
        for company in self:
            r = settings.inexchange_request_token('POST',url,
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

    def add_users(self):
        settings = self.env['res.config.settings']
        url = settings.get_url(endpoint='companies/identifiers')
        settings.inexchange_request_client_token()
        for company in self:
            r = settings.inexchange_request_token('POST', url,
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
    
    def merge_invoice_address(self):
        for contact in self.env['res.partner'].search([]):
            if contact.type == 'invoice':
                if contact.name:
                    contact.company_type = 'company'
    
    def lookup_buyer_company(self):
        def match_buyer(entry):
            org_match = entry.get('orgNo') == self.company_org_number
            capability = entry.get('receiveElectronicInvoiceCapability') == 'ReceivingElectronicInvoices'
            return capability and org_match
            
            
        settings = self.env['res.config.settings']
        url = settings.get_url(endpoint='buyerparties/lookup')
        client_token = settings.inexchange_request_client_token()
        header = {
            'Content-Type': 'application/json',
            'ClientToken': client_token,
            
        }
        data = {
            'PartyId': self.company_org_number or False,
            'GLN': self.gln_number_vertel or False,
            'orgNo': self.company_org_number or False,
            'vatNo': self.vat or False
        }
        _logger.debug(' %s' %json.dumps(data))
        result = requests.post(url, headers=header, data=json.dumps(data))
        # ~ raise Warning(result.text)
        result_party = json.loads(result.text)["parties"]
        # ~ raise Warning(str(result_party))
        _logger.warn('Haze %s' %result_party)
        # ~ if self.commercial_partner_id.gln_number_vertel:
            # ~ for entry in result_party:
                # ~ _logger.info('Haze with gln%s' %entry)
                # ~ if entry['receiveElectronicInvoiceCapability'] =='ReceivingElectronicInvoices':
                    # ~ if entry.get('gln') == self.commercial_partner_id.gln_number_vertel:
                        # ~ self.commercial_partner_id.inexchange_company_id = entry["companyId"]
                        # ~ _logger.info('Haze %s' %entry["companyId"])
        if self.gln_number_vertel:
            for entry in result_party:
                _logger.info('Haze with gln%s' %entry)
                if entry['receiveElectronicInvoiceCapability'] =='ReceivingElectronicInvoices':
                    if entry.get('gln') == self.gln_number_vertel:
                        self.inexchange_company_id = entry["companyId"]
                        _logger.info('Haze %s' %entry["companyId"])
                    
            
        else:
            matches = [x for x in result_party if match_buyer(x)]
            if len(matches) == 0:
                # ~ return
                raise Warning('Failed to find')
            elif len(matches) > 1:
                if not self.inexchange_company_id:
                    companies = '\n'.join([f"{x['name']} with OrgNo:{x['orgNo']}, GLN: {x['gln']}, VAT:{x['vatNo']},CompanyID: {x['companyId']}" for x in matches])
                    raise Warning(f'Multiple matches for buyer:\n{companies}, \n Please select the one you would like to copy companyID')
            elif len(matches) == 1:
                self.inexchange_company_id = entry["companyId"]
        if not self.inexchange_company_id:
            # ~ return
            raise Warning('%s is not in Inexchange or can not accept EDI Invoice' % self.commercial_partner_id.name)
        # ~ _logger.info('Haze %s' %json.loads(result.text))
        if result.status_code not in (200,):
            raise Warning('Failed to check partner')
            
    # ~ @api.model
    # ~ def lookup_buyer_companies(self):
        # ~ for partner in self.env['res.partner'].search([]):
            # ~ partner.lookup_buyer_company()
            # ~ time.sleep(0.5)

class Sale_order(models.Model):
    _inherit='sale.order'
    customer_payment_mode_id = fields.Many2one(comodel_name="account.payment.mode", string="Payment Mode", related = "partner_id.customer_payment_mode_id", readonly = True)
