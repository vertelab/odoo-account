# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import requests
from datetime import datetime, timedelta
import time

from odoo import api, fields, models
from odoo.exceptions import Warning

_logger = logging.getLogger(__name__)


class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    inexchange_invoice_url_address = fields.Char(string='Inexchange Invoice UUID', help = "This is for inexchange document ID" )
    inexchange_invoice_uri_id = fields.Char(string='Inexchange Invoice Id', help = "This is for inexchange invoice ID" )
    inexchange_erp_id = fields.Char(string='Inexchange ERP document ID', help = "This is for inexchange ERP" )
    # ~ inexchange_invoice_status = fields.Char(string='Inexchange Invoice Status', help = 'This is for inexchange invoice status')
    inexchange_error_status = fields.Char(string='Inexchange Invoice Error Message', help = 'This is for inexchange invoice Message')
    error_find = fields.Boolean(string="Inexchange invoice has errors",help = 'This is for inexchange invoice error')
    is_inexchange_invoice = fields.Boolean(string="Invoice has been sent to Inexchange",help = 'This is for inexchange invoice')
    inexchange_file_count = fields.Integer(default = 0)

    def upload_invoice(self, data):
        settings = self.env['res.config.settings']
        url = settings.get_url(endpoint='documents')
        client_token = settings.inexchange_request_client_token()
        # ~ raise Warning(client_token)
        _logger.info('Haze client token : %s ' %client_token)
        self.inexchange_file_count += 1
        # ~ raise Warning(self.partner_id.customer_payment_mode_id.id)
        # ~ for invoice in self:
        header = {
            'ClientToken': client_token,
            'ContentDisposition': 'attachement; filename=%s-%s.xml'%(self.reference.replace('/',''), self.inexchange_file_count),
            }
        # ~ raise Warning(str(header))
        result = requests.post(
            url, headers=header, files={
              'File': (self.reference.replace('/','') + str(self.inexchange_file_count), data, 'application/xml')})
        _logger.warning('Haze %s ' %result.status_code)
        _logger.warn(f'Haze {result.text}')
        _logger.warn(f'Haze {result.headers}')
        self.inexchange_invoice_uri_id = str(result.headers['Location'])
        _logger.info('HaLu %s' %str(result.headers['Location']))
        if result.status_code not in [202,200]:
            raise Warning('Failed to upload invoice')
        return result

    def send_uploaded_invoice(
            self, xml_file_ref, pdf_file_ref=None, attachments=None):
        settings = self.env['res.config.settings']
        client_token = settings.inexchange_request_client_token()
        url = settings.get_url(endpoint='documents/outbound')

        for invoice in self:
            
            header = {
                    'ClientToken': client_token,
                    'Content-Type': 'application/json'}
            if invoice.partner_id.commercial_partner_id.email and not invoice.partner_id.commercial_partner_id.inexchange_company_id and invoice.partner_id.customer_payment_mode_id.id != 1:
                data = {
                    "sendDocumentAs": {
                        "type": "PDF",
                        # ~ "paper": {
                            # ~ "recipientAddress": {
                                # ~ "name": invoice.partner_id.name,
                                # ~ "department": None,
                                # ~ "streetName": invoice.partner_id.street,
                                # ~ "postBox": None,
                                # ~ "postalZone": invoice.partner_id.zip,
                                # ~ "city": invoice.partner_id.city,
                                # ~ "countryCode": "SE"
                                # ~ },
                            # ~ "returnAddress": {
                                # ~ "name": self.env.user.company_id.name,
                                # ~ "department": None,
                                # ~ "streetName": self.env.user.company_id.street,
                                # ~ "postBox": None,
                                # ~ "postalZone": self.env.user.company_id.zip,
                                # ~ "city": self.env.user.company_id.city,
                                # ~ "countryCode": "SE"
                                # ~ }
                        # ~ },
                    "pdf": {
                        "recipientEmail": invoice.partner_id.commercial_partner_id.email,
                        "recipientName": invoice.partner_id.commercial_partner_id.name,
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
                _logger.info('Haze Uri: %s ' %xml_file_ref)
            elif invoice.partner_id.inexchange_company_id and invoice.partner_id.customer_payment_mode_id.id == 1:
                data = {
                    "sendDocumentAs": {
                        "type": "Electronic",
                        "Electronic": {
                            "RecipientID": invoice.partner_id.commercial_partner_id.inexchange_company_id or invoice.partner_id.inexchange_company_id,
                            }
                    },
                    "recipientInformation": {
                        "gln": invoice.partner_id.gln_number_vertel or False,  # noqa:E501
                        "orgNo": invoice.partner_id.company_org_number,  # noqa:E501
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
                _logger.info('Haze Uri: %s ' %xml_file_ref)
            # ~ raise Warning(data["Electronic"]["RecipientID"])
            data['document']["renderedDocumentFormat"] = "application/pdf"
            # ~ data['document']["renderedUri"] = invoice.inexchange_invoice_uri_id
            if attachments:
                data['document']['attachments'] = attachments
            data = json.dumps(data)
            result = requests.post(url, headers=header, data=data)
            # ~ result = json.loads(result.text)
            _logger.info('HaLu result 1 %s' % str(result.headers))
            
            # ~ _logger.info('HaLu result 2 %s' % result)
            location = result.headers['Location'].split('/')[-1]
            _logger.info('HaLu result %s' % location)
            invoice.inexchange_invoice_url_address = location
            
        
            if not result.status_code in [200]:
                raise Warning(f'Failed to send invoice\n Failed with:\n{result.status_code}\n{jsonb.dumps(result.text)}')
                
            return result
            
    @api.one
    def inexchange_get_invoice_status(self):
        settings = self.env['res.config.settings']
        client_token = settings.inexchange_request_client_token()
        url = settings.get_url(endpoint='invoices/outbound/%s' %self.inexchange_invoice_url_address)
        _logger.info('Haze url %s' %url)
        
        header = {
            'ClientToken': client_token,
            'Content-Type': 'application/json',
            'Accept' : '*/*'}
        result = requests.get(url, headers = header)
        
        self.inexchange_invoice_status = result.content
        _logger.info('Haze result %s' %str(result))
        _logger.info('Haze header %s' %str(header))
        _logger.info('Haze status code %s' %result.status_code)
        if not result.status_code in [200,202]:
            raise Warning(f'Failed to send invoice\n Failed with:\n{result.status_code}\n{result.content}')
            
    @api.model
    def inexchange_get_all_invoice_status(self):
        settings = self.env['res.config.settings']
        client_token = settings.inexchange_request_client_token()
        url = settings.get_url(endpoint='documents/outbound/list' )
        _logger.info('Haze url %s' %url)
        header = {
            'ClientToken': client_token,
            'Content-Type': 'application/json',
            'Accept' : 'application/json'}
        
        data = {
            "take":50,
            "skip":0,
            "createdFrom": "%sZ" %str(fields.Datetime().now()+timedelta(days=-1)).replace(' ','T'),
            "createdTo": "%sZ" %str(fields.Datetime().now()).replace(' ','T'),
            "updatedAfter": "%sZ" %str(fields.Datetime().now()+timedelta(days=-1)).replace(' ','T'),
            "documentType": "invoice",
            "status": "Errors",
            "includeFileInfo": True,
            "includeErrorInfo": True
        }

        result = requests.post(url, headers = header, data = json.dumps(data))
        result = json.loads(result.text)
        documents = result['documents']
        _logger.info('%s Haze document' % documents)
        for document in documents:
            inexchange_error_doc_id = document.get('id',False)
            error = document.get('error', False)
            invoice_inexchange_id = self.env['account.invoice'].search([('inexchange_invoice_url_address','=',document['id'])], limit=1)
            _logger.info('Inexchange Error Info %s' % invoice_inexchange_id.inexchange_invoice_url_address)
            
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
            'Accept' : '*/*'}
        result = requests.get(url, headers = header)
        _logger.info(result.text)
        if not result.status_code in [200]:
            raise Warning('Failed to fetch invoice')
        else:
            raise Warning(result.text)
        return result
            
            
    @api.multi
    def download_invoice(self,file_location):    
        settings = self.env['res.config.settings']
        client_token = settings.inexchange_request_client_token()
        for invoice in self:
            if invoice.file_location:
                header = {
                'ClientToken': client_token,
                'Accept' : '*/*'}
                result = requests.get(file_location, headers = header)
                _logger.info(result.text)
                if not result.status_code in (200,):
                    raise Warning('Failed to download invoice')
                return result
    @api.multi
    def send_invoice_to_inexchange_action(self):
        for invoice in self:
            if invoice.partner_id.inexchange_company_id:
                invoice.name = invoice.reference
                invoice.inexchange_error_status = None
                version = invoice.get_ubl_version()
                xml_string = invoice.generate_ubl_xml_string(version = version)
                _logger.info(xml_string)
                result = invoice.upload_invoice(xml_string)
                result = invoice.send_uploaded_invoice(invoice.inexchange_invoice_uri_id)
                invoice.is_inexchange_invoice = True
            elif not invoice.partner_id.inexchange_company_id and invoice.partner_id.customer_payment_mode_id.id == 1 :
                raise Warning('%s does not have an inexchange company Id, therefore they can not accept EDI invoice, please doubble check it.' %(invoice.partner_id.name or invoice.partner_id.commercial_partner_id.name))
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
                


