# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import requests

from odoo import api, fields, models
from odoo.exceptions import Warning

_logger = logging.getLogger(__name__)


class account_invoice(models.Model):
    _inherit = 'account.invoice'

    def upload_invoice(self, data):
        settings = self.env['res.config.settings']
        url = settings.get_url(endpoint='documents')
        client_token = settings.inexchange_request_client_token()
        for invoice in self:
            header = {
                'ClientToken': client_token,
                'ContentDisposition': 'attachement; filename="invoice.xls"',
                }
        result = requests.post(
            url, headers=header, files={
              'file': ('invoice.xls', data, 'application/xml')})
        if result.status_code not in (202,):
            raise Warning('Failed to upload invoice')
        return result

    def send_uploaded_invoice(
            self, xml_file_ref, pdf_file_ref=None, attachments=None):
        settings = self.env['res.config.settings']
        client_token = settings.inexchange_request_client_token()
        url = settings.get_url(endpoints='documents/outbound')

        for invoice in self:
            header = {
                'ClientToken': client_token,
                'Content-Type': 'application/json'}
            data = {
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
                    "gln": invoice.partner_id.commercial_partner_id.id_numbers.name,  # noqa:E501
                    "orgNo": invoice.partner_id.commercial_partner_id.company_registry,  # noqa:E501
                    "vatNo": invoice.partner_id.commercial_partner_id.vat,
                    "name": invoice.partner_id.name,
                    "recipientNo": "1",
                    "countryCode": "SE"
                    },
                "document": {
                    "documentFormat": "syntaxbindning",
                    "documentUri": xml_file_ref,
                    "language": "sv-SE",
                    "culture": "sv-SE"
                    }}
            if pdf_file_ref:
                data['document']["renderedDocumentFormat"] = "application/pdf"
                data['document']["renderedDocumentUri"] = pdf_file_ref
            if attachments:
                data['document']['attachments'] = attachments

    def invoice_status(self):
        for invoice in self:
            url = "%s" % invoice.name
            r = self.env['res.config.settings'].inexchange_request_token(
                'GET', url)
            r = json.loads(r)
            _logger.debug('Haze4 %s' %r)

    def fetch_invoice(self):
        settings = self.env['res.config.settings']
        client_token = settings.inexchange_request_client_token()
        url = settings.get_url('documents/incoming?type=invoice')
        for invoice in self:
            # Fetch invoice here!
            _logger.info(client_token + url)

    def download_invoice(self):
        settings = self.env['res.config.settings']
        for invoice in self:
            if invoice.name:
                url = settings.get_url(f'documents/{invoice.name}')
                # Download invoice here.
                _logger.warn(url)

    @api.multi
    def mark_invoice_as_handled(self):
        settings = self.env['res.config.settings']
        for invoice in self:
            if invoice.name:
                url = settings.get_url('documents/handled')
                # Mark as handled here
                _logger.warn(url)


class AccountInvoiceSend(models.TransientModel):
    _inherit = 'account.invoice.send'

    is_inexchange = fields.Boolean(string='InExchange', default=True)

    @api.multi
    def send_and_print_action(self):
        res = super(AccountInvoiceSend, self).send_and_print_action()
        if self.is_inexchange:
            for invoice in self.invoice_ids:
                xml_string = invoice.generate_ubl_xml_string()
                result = invoice.upload_invoice(xml_string)
                return res
                invoice.send_uploaded_invoice(result)
                status = invoice.invoice_status()
                _logger.info(status)
        return res
