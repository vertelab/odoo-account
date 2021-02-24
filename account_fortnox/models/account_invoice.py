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
    
    @api.multi
    def fortnox_create(self):
        # Customer (POST https://api.fortnox.se/3/customers)
        for invoice in self:
            if not invoice.date_due:
                raise Warning("ERROR: missing date_due on invoice.")
            if not invoice.partner_id.commercial_partner_id.ref:
                invoice.partner_id.partner_create()
            if invoice.partner_id.commercial_partner_id.ref:
                invoice.partner_id.partner_update()
            InvoiceRows = []
            for line in invoice.invoice_line_ids:
                if line.product_id:
                    line.product_id.article_update()
                InvoiceRows.append(
                        {
                            "AccountNumber": line.account_id.code,
                            "DeliveredQuantity": line.quantity,
                            "Description": line.name,
                            "ArticleNumber": line.product_id.default_code if line.product_id else None,
                            "Price":line.price_unit,
                            # ~ "Unit": "st",
                            "VAT": int(line.invoice_line_tax_ids.mapped('amount')[0]) if len(line.invoice_line_tax_ids) > 0 else None,
                        })
            r = self.company_id.fortnox_request('post',"https://api.fortnox.se/3/invoices",
                data={                   
                    "Invoice": {
                        "Comments": "",
                        # ~ "Credit": True if invoice.type == "out_refund" else False,
                        # ~ "CreditInvoiceReference": 0,
                        "Currency": "SEK",
                        "CustomerName": invoice.partner_id.commercial_partner_id.name,
                        "CustomerNumber": invoice.partner_id.commercial_partner_id.ref,
                        "DueDate":invoice.date_due.strftime('%Y-%m-%d'),
                        "InvoiceDate": invoice.date_invoice.strftime('%Y-%m-%d'),
                        "InvoiceRows": InvoiceRows,
                        "InvoiceType": "INVOICE",
                        "Language": "SV",
                        "Remarks": "",
                    }
                })
            
            r = json.loads(r)

            if r.get('ErrorInformation'):
                invoice._message_log(body='Error Creating Invoice Fortnox %s ' % r['ErrorInformation']['message'], subject='Fortnox Error')
                raise Warning('%s has prolem in its contact information, please check it' % invoice.partner_id.name)
                break
            else:
                invoice.ref = r["Invoice"]["CustomerNumber"]
                invoice.name = r["Invoice"]["DocumentNumber"]
            return r
    
        
