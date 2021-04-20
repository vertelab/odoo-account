# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import requests
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class account_invoice(models.Model):
    _inherit = 'account.invoice'

    inexchange_invoice_url_address = fields.Char(
        string='Inexchange Invoice UUID',
        help="This is for inexchange document ID")
    inexchange_invoice_uri_id = fields.Char(
        string='Inexchange Invoice Id',
        help="This is for inexchange invoice ID")
    inexchange_erp_id = fields.Char(
        string='Inexchange ERP document ID',
        help="This is for inexchange ERP")
    # ~ inexchange_invoice_status = fields.Char(string='Inexchange Invoice Status', help = 'This is for inexchange invoice status')
    inexchange_error_status = fields.Char(
        string='Inexchange Invoice Error Message',
        help='This is for inexchange invoice Message')
    error_find = fields.Boolean(
        string="Inexchange invoice has errors",
        help='This is for inexchange invoice error')
    is_inexchange_invoice = fields.Boolean(
        string="Invoice has been sent to Inexchange",
        help='This is for inexchange invoice')
    inexchange_file_count = fields.Integer(default=0)

    def upload_invoice(self, data):
        settings = self.env['res.config.settings']
        url = settings.get_url(endpoint='documents')
        client_token = settings.inexchange_request_client_token()
        self.inexchange_file_count += 1
        filename = (f"{self.reference.replace('/', '')}-"
                    f"{self.inexchange_file_count}")
        header = {
            'ClientToken': client_token,
            'ContentDisposition': f'attachement; filename={filename}.xml',
            }
        result = requests.post(
            url, headers=header, files={
              'File': (filename, data, 'application/xml')})
        self.inexchange_invoice_uri_id = str(result.headers['Location'])
        if result.status_code not in (202, 200):
            raise UserError('Failed to upload invoice')
        return result

    def send_uploaded_invoice(
            self, xml_file_ref, pdf_file_ref=None, attachments=None):
        settings = self.env['res.config.settings']
        client_token = settings.inexchange_request_client_token()
        url = settings.get_url(endpoint='documents/outbound')

        for invoice in self:
            # ToDo: Add variables to be able to use paper invoice.
            # paper = {
            #     "recipientAddress": {
            #         "name": invoice.partner_id.name,
            #         "department": None,
            #         "streetName": invoice.partner_id.street,
            #         "postBox": None,
            #         "postalZone": invoice.partner_id.zip,
            #         "city": invoice.partner_id.city,
            #         "countryCode": "SE"
            #         },
            #     "returnAddress": {
            #         "name": self.env.user.company_id.name,
            #         "department": None,
            #         "streetName": self.env.user.company_id.street,
            #         "postBox": None,
            #         "postalZone": self.env.user.company_id.zip,
            #         "city": self.env.user.company_id.city,
            #         "countryCode": "SE"
            #         }
            #     }
            header = {
                    'ClientToken': client_token,
                    'Content-Type': 'application/json'}
            try:
                peppol_id = self.env.ref(
                    'account_inexchange.account_payment_mode_peppol').id
            except Exception:
                _logger.warning(
                    'Could nog find: '
                    '"account_inexchange.account_payment_mode_peppol"')
                peppol_id = False
            if (invoice.partner_id.commercial_partner_id.email
                    and not invoice.partner_id.commercial_partner_id.inexchange_company_id  # noqa:E501
                    and invoice.payment_mode_id.id != peppol_id):
                data = {
                    "sendDocumentAs": {
                        "type": "PDF",
                        "pdf": {
                            "recipientEmail": invoice.partner_id.commercial_partner_id.email,  # noqa:E501
                            "recipientName": invoice.partner_id.commercial_partner_id.name,  # noqa:E501
                            "senderEmail": self.env.user.email,
                            "senderName": self.env.user.name
                            }
                        },
                    "recipientInformation": {
                        "gln": invoice.partner_id.commercial_partner_id.gln_number_vertel or False,  # noqa:E501
                        "orgNo": invoice.partner_id.commercial_partner_id.company_org_number,  # noqa:E501
                        "vatNo": invoice.partner_id.vat or False,
                        "name": invoice.partner_id.name,
                        "recipientNo": "1",
                        "countryCode": "SE"
                        },
                    "document": {
                        "documentFormat": "bis3",
                        "documentUri": xml_file_ref,
                        "language": "sv-SE",
                        "culture": "sv-SE"
                        }}
            elif (invoice.partner_id.inexchange_company_id
                  and invoice.payment_mode_id.id == peppol_id):
                data = {
                    "sendDocumentAs": {
                        "type": "Electronic",
                        "Electronic": {
                            "RecipientID":
                                invoice.partner_id.commercial_partner_id.inexchange_company_id
                                or invoice.partner_id.inexchange_company_id,
                            }
                    },
                    "recipientInformation": {
                        "gln": invoice.partner_id.gln_number_vertel or False,
                        "orgNo": invoice.partner_id.company_org_number,
                        "vatNo": invoice.partner_id.vat or False,
                        "name": invoice.partner_id.name,
                        "recipientNo": "1",
                        "countryCode": "SE"
                        },
                    "document": {
                        "documentFormat": "bis3",
                        "documentUri": xml_file_ref,
                        "language": "sv-SE",
                        "culture": "sv-SE"
                        }}
            else:
                raise UserError('Could not find a valid send mode')
            data['document']["renderedDocumentFormat"] = "application/pdf"
            if attachments:
                data['document']['attachments'] = attachments
            data = json.dumps(data)
            result = requests.post(url, headers=header, data=data)
            location = result.headers['Location'].split('/')[-1]
            invoice.inexchange_invoice_url_address = location

            if result.status_code not in [200]:
                raise UserError('Failed to send invoice\n'
                                'Failed with:\n'
                                f'{result.status_code}\n'
                                f'{json.dumps(result.text)}')
            return result

    @api.one
    def inexchange_get_invoice_status(self):
        settings = self.env['res.config.settings']
        client_token = settings.inexchange_request_client_token()
        url = settings.get_url(endpoint='invoices/outbound/%s' % self.inexchange_invoice_url_address)
        header = {
            'ClientToken': client_token,
            'Content-Type': 'application/json',
            'Accept': '*/*'}
        result = requests.get(url, headers=header)
        self.inexchange_invoice_status = result.content
        if result.status_code not in (200, 202):
            raise UserError(f'Failed to send invoice\n Failed with:\n{result.status_code}\n{result.content}')

    @api.model
    def inexchange_get_all_invoice_status(self):
        settings = self.env['res.config.settings']
        client_token = settings.inexchange_request_client_token()
        url = settings.get_url(endpoint='documents/outbound/list')
        header = {
            'ClientToken': client_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json'}

        data = {
            "take": 50,
            "skip": 0,
            "createdFrom": "%sZ" % str(fields.Datetime().now()+timedelta(days=-1)).replace(' ', 'T'),
            "createdTo": "%sZ" % str(fields.Datetime().now()).replace(' ', 'T'),
            "updatedAfter": "%sZ" % str(fields.Datetime().now()+timedelta(days=-1)).replace(' ', 'T'),
            "documentType": "invoice",
            "status": "Errors",
            "includeFileInfo": True,
            "includeErrorInfo": True
        }

        result = requests.post(url, headers=header, data=json.dumps(data))
        result = json.loads(result.text)
        documents = result['documents']
        for document in documents:
            inexchange_error_doc_id = document.get('id', False)
            error = document.get('error', False)
            invoice_inexchange_id = self.env['account.invoice'].search(
                [('inexchange_invoice_url_address', '=', document['id'])],
                limit=1)
            _logger.info('Inexchange Error Info '
                         f'{invoice_inexchange_id.inexchange_invoice_url_address}')

            if invoice_inexchange_id:
                invoice_inexchange_id.error_find = True
                invoice_inexchange_id.inexchange_error_status = document['error']
                _logger.info('Inexchange Error Info %s' % invoice_inexchange_id.inexchange_error_status)
                invoice_inexchange_id.error_find = True
        return result

    def reset_inexchange_invoice_error_status(self):
        for invoice in self:
            if invoice.inexchange_error_status:
                invoice.inexchange_error_status = None

    def fetch_invoice(self):
        settings = self.env['res.config.settings']
        client_token = settings.inexchange_request_client_token()
        url = settings.get_url(endpoint='documents/incoming?type=invoice')
        # Fetch invoice here!
        header = {
            'ClientToken': client_token,
            'Accept': '*/*'}
        result = requests.get(url, headers=header)
        _logger.info(result.text)
        if result.status_code not in (200,):
            raise UserError('Failed to fetch invoice')
        else:
            raise UserError(result.text)
        return result

    @api.multi
    def download_invoice(self, file_location):
        settings = self.env['res.config.settings']
        client_token = settings.inexchange_request_client_token()
        for invoice in self:
            if invoice.file_location:
                header = {
                    'ClientToken': client_token,
                    'Accept': '*/*'}
                result = requests.get(file_location, headers=header)
                _logger.info(result.text)
                if result.status_code not in (200,):
                    raise UserError('Failed to download invoice')
                return result

    @api.multi
    def send_invoice_to_inexchange_action(self):
        for invoice in self:
            if invoice.partner_id.inexchange_company_id:
                invoice.name = invoice.reference
                invoice.inexchange_error_status = None
                version = invoice.get_ubl_version()
                xml_string = invoice.generate_ubl_xml_string(version=version)
                _logger.info(xml_string)
                result = invoice.upload_invoice(xml_string)
                _logger.info(f'Invoice upload: {result.text}')
                result = invoice.send_uploaded_invoice(invoice.inexchange_invoice_uri_id)
                _logger.info(f'Invoice upload: {result.text}')
                invoice.is_inexchange_invoice = True
            elif not invoice.partner_id.inexchange_company_id and invoice.partner_id.payment_mode_id.id == 1:
                raise UserError('%s does not have an inexchange company Id, therefore they can not accept EDI invoice, please doubble check it.' % (invoice.partner_id.name or invoice.partner_id.commercial_partner_id.name))
        # ~ return res
    # ~ @api.multi
    # ~ def mark_invoice_as_handled(self):
        # ~ settings = self.env['res.config.settings']
        # ~ client_token = settings.inexchange_request_client_token()
        # ~ for invoice in self:
            # ~ result = invoice.fetch_invoice()
            # ~ if result.headers['id']:
                # ~ url = settings.get_url(endpoint='documents/handled')
                # ~ header = {
                # ~ 'ClientToken': client_token,
                # ~ 'Content-Type': 'application/json',
                # ~ 'Accept' : "*/*{
                # ~ "documents" : [result.headers['id']]
                # ~ }"}
                # ~ _logger.info(result.text)
                # ~ if not result.status_code in (200,):
                    # ~ raise Warning('Failed to mark invoices as handled')
                # ~ return result
