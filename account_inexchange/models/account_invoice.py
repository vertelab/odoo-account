# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import Warning
import warnings
import time

from datetime import datetime
import requests
import json

import logging
_logger = logging.getLogger(__name__)


class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    def upload_invoice(self):
        url = "https://testapi.inexchange.se/v1/api/documents"
        # ~ client_token = self.env['res.config.settings'].inexchange_request_client_token()
        for invoice in self:
            r = self.env['res.config.settings'].inexchange_invoice_upload('POST', url)
            _logger.warn('HazeR %s' %r)
            # ~ r = json.loads(js.decode(r))
            response = requests.get(url)
            # ~ data= response.json()
            # ~ location = data['Location']
            # ~ _logger.warn('Hazedata %s'%response)
            # ~ invoice.name = r.location
            #It has a location to send back but I can not get it out...
            _logger.warn('Haze1+ %s' %invoice.name)
                
    def send_uploaded_invoice(self):
        #all infomation are in the log, but because of other problems, it can not be upload to inexchange, I have 
        # to fix boundary first and then get the location string back then this step will be processed.
        url = "https://testapi.inexchange.se/v1/api/documents/outbound"
        for invoice in self:
            data = {}
            r = self.env['res.config.settings'].inexchange_request_token('POST', url,
                data={
                "sendDocumentAs": {
                    "type": "PDF",
                    "paper": {
                      "recipientAddress": {
                        "name": invoice.partner_id.name,
                        "department": None,
                        "streetName": invoice.partner_id.street,
                        "postBox": None,
                        "postalZone": invoice.partner_id.zip,
                        "city": invoice.partner_id.city,
                        "countryCode": "SE"
                      },
                      "returnAddress": {
                        "name": self.env.user.company_id.name,
                        "department": None,
                        "streetName": self.env.user.company_id.street,
                        "postBox": None,
                        "postalZone": self.env.user.company_id.zip,
                        "city": self.env.user.company_id.city,
                        "countryCode": "SE"
                      }
                    },
                    "pdf": {
                      "recipientEmail": invoice.partner_id.email,
                      "recipientName": invoice.partner_id.name,
                      "senderEmail": self.env.user.company_id.email,
                      "senderName": self.env.user.company_id.name
                    }
                  },
                  "recipientInformation": {
                    "gln": invoice.partner_id.commercial_partner_id.id_numbers.name,
                    "orgNo": invoice.partner_id.commercial_partner_id.company_registry,
                    "vatNo": invoice.partner_id.commercial_partner_id.vat,
                    "name": invoice.partner_id.name,
                    "recipientNo": "1",
                    "countryCode": "SE"
                  },
                  "document": {
                    "documentFormat": "syntaxbindning",
                    # ~ "documentUri": "urn:inexchangedocument:4a149d3d-da2d-4d77-9046-694e4ef7b111",
                    "renderedDocumentFormat": "application/pdf",
                    # ~ "renderedDocumentUri": "urn:inexchangedocument:4a149d3d-da2d-4d77-9046-694e4ef7b111",
                    "attachments": [
                      "urn:inexchangedocument:4a149d3d-da2d-4d77-9046-694e4ef7b111"
                    ],
                    "language": "sv-SE",
                    "culture": "sv-SE"
                  }
                })
            # ~ r = json.loads(r)
            
            _logger.warn('Haze3 %s' %invoice.name)
            _logger.warn('Haze2 %s' %r)
    
    def invoice_status(self):
        for invoice in self:
            url = "%s" % invoice.name
            r = self.env['res.config.settings'].inexchange_request_token('GET', url)
            r = json.loads(r)
            _logger.debug('Haze4 %s' %r)
            
            
            
    def fetch_invoice(self):
        self.env['res.config.settings'].inexchange_request_client_token()
        url = "https://testapi.inexchange.se/v1/api/documents/incoming?type=invoice"
        for invoice in self:
            
            r = self.env['res.config.settings'].inexchange_request_token('GET', url)
            r = json.loads(r)
            invoice.name = r['documents']['id']
            
    def download_invoice(self):
        for invoice in self:
            if invoice.name:
                url = "https://testapi.inexchange.se/v1/api/documents/%s" %invoice.name
                r = self.env['res.config.settings'].inexchange_request_token('GET', url)
            r = json.loads(r)
    @api.multi
    def mark_invoice_as_handled(self):
        for invoice in self:
            if invoice.name:
                url = "https://testapi.inexchange.se/api/documents/handled" 
                r = self.env['res.config.settings'].inexchange_request_token('POST',url,
                    data={
                    "documents":[invoice.name]
                    })
            r = json.loads(r)
                
            
class AccountInvoiceSend(models.TransientModel):
    _inherit = 'account.invoice.send'

    is_inexchange = fields.Boolean(string='InExchange',default=True)
    
    
    @api.multi
    def send_and_print_action(self):
        res = super(AccountInvoiceSend, self).send_and_print_action()
        if self.is_inexchange:
            for invoice in self.invoice_ids:
                # ~ time.sleep(1)
                # ~ if not invoice.name:
                # ~ raise Warning(invoice)
                invoice.upload_invoice()
                invoice.send_uploaded_invoice()
                invoice.invoice_status()
        return res            
            
            
    
    
        
