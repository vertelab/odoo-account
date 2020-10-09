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
                raise Warning("Please select payment term")
            if not invoice.partner_id.commercial_partner_id.ref:
                # ~ raise Warning("You have not updated this customer to the fortnox list.")
                # ~ ref = invoice.partner_id.commercial_partner_id.fortnox_update()
                ref = invoice.partner_id.fortnox_update()
            InvoiceRows = []
            for line in invoice.invoice_line_ids:
                InvoiceRows.append(
                        {
                            "AccountNumber": line.account_id.code,
                            "DeliveredQuantity": line.quantity,
                            "Description": line.name,
                            "Price":line.price_unit,
                            # ~ "Unit": "st",
                            # ~ "VAT": int(line.invoice_line_tax_ids.mapped('amount')[0]),
                        })
            r = self.company_id.fortnox_request('post',"https://api.fortnox.se/3/invoices",
                data={                   
                "Invoice": {
                    "Comments": "",
                    # ~ "Credit": "false",
                    "CreditInvoiceReference": 0,
                    "Currency": "SEK",
                    "CustomerName": invoice.partner_id.commercial_partner_id.name,
                    "CustomerNumber": invoice.partner_id.commercial_partner_id.ref,
                    "DueDate":invoice.date_due.strftime('%Y-%m-%d'),
                    "InvoiceDate": invoice.date_invoice.strftime('%Y-%m-%d'),
                    "InvoiceRows": InvoiceRows,
                    "InvoiceType": "INVOICE",
                    "Language": "SV",
                    # ~ "Net": 1590,
                    "Remarks": "",
                    # ~ "Sent": false,
                    # ~ "TermsOfPayment": invoice.payment_term_id.name,
                    # ~ "Total": 1988,
                    # ~ "TotalToPay": 1988,
                    # ~ "TotalVAT": 397.5,
                }
            })
            
            r = json.loads(r)
            # ~ if not r["Invoice"]["CustomerNumber"]:
            # ~ raise Warning(str(r))
            invoice.ref = r["Invoice"]["CustomerNumber"]
            return r
            
