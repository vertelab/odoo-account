# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import Warning
import warnings

from datetime import datetime
import requests
import json

import logging
_logger = logging.getLogger(__name__)


class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    def upload_invoice(self,client_token,data):
        url = "https://testapi.inexchange.se/v1/api/documents"
        for invoice in self:
            r = self.env['res.config.settings'].inexchange_request_token('POST', url,
                headers={
                "ClientToken": self.env['ir.config_parameter'].sudo().get_param('inexchange.client.token'),
                "Host": "testapi.inexchange.se",
                "Content-Type": "multipart/form-data; boundary=X-TEST-BOUNDARY",
                "Accept": "*/*",
                "Content-Length": len(data),
                
                --X-TEST-BOUNDARY--
                "Content-Disposition": 'form-data; name="File"; filename="testfile.xml"',
                "Content-Type": "application/xml",
                # ~ --X-TEST-BOUNDARY--
                })
            r = json.loads(r)
                
    def send_uploaded_invoice(self,env,client_token,invoice):
        
        url = "https://%s/v1/api/outbound" % self.env['ir.config_parameter'].sudo().get_param('inexchange.test.host') if env == "test" else self.env['ir.config_parameter'].sudo().get_param('inexchange.real.host')
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
                    "gln": invoice.partner_id.commercial_partner_id.id_number.name,
                    "orgNo": invoice.partner_id.commercial_partner_id.company_registry,
                    "vatNo": invoice.partner_id.commercial_partner_id.vat,
                    "name": invoice.partner_id.name,
                    "recipientNo": "1",
                    "countryCode": "SE"
                  },
                  "document": {
                    "documentFormat": "UBL-Invoice-2.1",
                    "documentUri": "urn:inexchangedocument:4a149d3d-da2d-4d77-9046-694e4ef7b111",
                    "renderedDocumentFormat": "application/pdf",
                    "renderedDocumentUri": "urn:inexchangedocument:4a149d3d-da2d-4d77-9046-694e4ef7b111",
                    "attachments": [
                      "urn:inexchangedocument:4a149d3d-da2d-4d77-9046-694e4ef7b111"
                    ],
                    "language": "sv-SE",
                    "culture": "sv-SE"
                  }
                })
            r = json.loads(r)
            
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
                
            
            
            
            
    
    
        
