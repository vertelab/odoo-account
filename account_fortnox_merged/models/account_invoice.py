1# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
import logging
import json
import time

from odoo import api, fields, models, _
from odoo.exceptions import Warning, UserError

_logger = logging.getLogger(__name__)

BASE_URL = 'https://api.fortnox.se'

class AccountInvoice(models.Model):
    _inherit = "account.move"
    fortnox_response = fields.Char(string="Fortnox Response", readonly=True)
    fortnox_status = fields.Char(string="Fortnox Status", readonly=True)
    # state = fields.Selection([("draft", "Utkast"), ("open", "Bekräftad"), ("sent", "Skickad"), ("paid", "Betalad"), ("cancel", "Avbruten")], readonly=False)

    def remove_zero_cost_lines(self):
        """
        SFM does not want products with 0 cost to show on the invoice.
        Call this function to remove them.
        """
        self.state = 'draft'
        for line in self.invoice_line_ids:
            if line.price_unit == 0 and line.quantity == 0:
                line.unlink()
        self.state = 'posted'

    def remove_package_products(self):
        """
        SFM does not want package products to show on the invoice.
        Call this function to remove them.
        This function is replaced remove_zero_cost_lines()
        """
        self.state = 'draft'
        for line in self.invoice_line_ids:
            if len(line.product_id.membership_product_ids) > 0 and line.price_unit == 0 and line.quantity == 0:
                line.unlink()
        self.state = 'posted'

    def update_invoice_status_fortnox_paid(self, fortnox_values):
        final_pay_date_string = fortnox_values.get('FinalPayDate')
        final_pay_date = datetime.strptime(final_pay_date_string, '%Y-%m-%d').date()
        fortnox_journal = self.env['account.journal'].search([('name','like','fortnox'),('type','=','bank')])

        if not fortnox_journal:
            raise UserError("No valid Journal found. Create a journal called something containing fortnox and of the type bank.")
        elif len(fortnox_journal) > 1:
            raise UserError("More than one valid journal found for fortnox. Make sure there is only one journal of the type Bank with fortnox in its name.")
        for rec in self:
            payment_methods = (rec.residual>0) and rec.journal_id.inbound_payment_method_ids or rec.journal_id.outbound_payment_method_ids
            payment_register_params = dict(
                amount = rec.residual,
                communication = rec.reference,
                currency_id = rec.currency_id.id,
                journal_id = fortnox_journal.id,
                payment_date = final_pay_date if final_pay_date else rec.date,
                payment_method_id = payment_methods and payment_methods[0].id or False,
                payment_type = rec.residual >0 and 'inbound' or 'outbound',
                partner_id = rec.partner_id.id,
            )

            payment_id = self.env['account.payment'].with_context(
                active_model='account.invoice',
                active_ids=rec.id,
            ).create(payment_register_params)

            payment_id._onchange_journal()
           # _logger.warning(f"before"*10)
           # _logger.warning(self.env.context)
           # _logger.warning(self.company_id)
           # _logger.warning(self.id)
            action = payment_id.action_validate_invoice_payment()
           # _logger.warning("after"*10)

    def update_invoice_status_fortnox_cron(self):
        """Update invoice status from fortnox."""

        # Assumption that most invoices are paid rather than canceled.
        # Python conserves dict order since Python 3.7 so order matters.
        states = {'fullypaid': 'paid',
                  'cancelled': 'cancel',}

        # States we don't care about.
        #          'unpaid': 'open',
        #          'unpaidoverdue': 'open'}

        # Cutof date to not check too old invoices.
        from_date = datetime.now() - timedelta(days=365)
        # Allow for multi company.
        for company in self.env['res.company'].search([]):
            for invoice in self.env['account.move'].search(
                    [('company_id', '=', company.id),
                     ('create_date', '>', from_date),
                     ('payment_state', '!=', 'paid'),
                     ('state', '!=', 'draft'),
                     ('state', '!=', 'cancel'),
                    ]):
                #('id', '=', 940)
                for state in states:
                    # Only allowed to do 4 requests per second to Fortnox.
                    # Do 3 requests per second just to be sure.
                    time.sleep(0.3)
                    try:
                        r = company.fortnox_request(
                            'get',
                            f'{BASE_URL}/3/invoices/{invoice.name}')
                            #f'{BASE_URL}/3/invoices/?filter={state}&documentnumber={invoice.name}&fromdate={from_date.strftime("%Y-%m-%d")}')                       
                        r = json.loads(r)
                    except:
                        _logger.error(f': {invoice.name}')
                        _logger.error(r.get('ErrorInformation'))
                        continue
                    
                    for inv in r.get('Invoice', []):
                        # ~ if invoice.name == inv.get('DocumentNumber'):
                        _logger.warning(f"{type(inv)} {inv=}")
                        inv_json = json.loads(inv)
                        
                        if invoice.name == inv_json['DocumentNumber']:
                            # ~ _logger.info(f' {invoice.id} {invoice.name}: {state}')
                            # ~ _logger.debug(str(invoice.read())) 
                            # ~ _logger.warning("Look here"*100)
                            # ~ _logger.warning(states[state])
                            # ~ _logger.warning(invoice.state)
                            if states[state] == 'paid' and invoice.state == 'posted':
                                invoice.update_invoice_status_fortnox_paid(inv_json)
                            elif states[state] == 'paid' and invoice.is_move_sent:
                                invoice.state = 'posted'
                                #TODO: check which method updates the state instead of setting it yourself. invoice.post something
                                invoice.update_invoice_status_fortnox_paid(inv_json)

                            invoice.fortnox_response = r
                            invoice.fortnox_status = states[state]
                            break
                    else:
                        # If we found an invoice we do not have to check
                        # next state.
                        break

    def fortnox_create(self):
        # Customer (POST https://api.fortnox.se/3/customers)
        for invoice in self:
            if not invoice.invoice_date_due:
                raise UserError(_("ERROR: missing date_due on invoice."))
            if not invoice.partner_id.commercial_partner_id.ref:
                invoice.partner_id.partner_create()
            if invoice.partner_id.commercial_partner_id.ref:
                invoice.partner_id.partner_update()
            InvoiceRows = []
            for line in invoice.invoice_line_ids:
                if line.product_id:
                    line.product_id.article_update()
                    InvoiceRows.append({
                        "AccountNumber": line.account_id.code,
                        "DeliveredQuantity": line.quantity,
                        "Description": line.name.replace('[','').replace(']','').strip(' '),
                        "ArticleNumber": line.product_id.default_code if line.product_id else None,
                        "Price": line.price_unit,
                        "VAT": int(line.tax_ids.mapped('amount')[0]) if len(line.tax_ids) > 0 else None,
                     })

            r = self.company_id.fortnox_request(
                'post',
                "https://api.fortnox.se/3/invoices",
                data={"Invoice": {
                    "Comments": "",
                    "Currency": "SEK",
                    "CustomerName": invoice.partner_id.commercial_partner_id.name,
                    "CustomerNumber": invoice.partner_id.commercial_partner_id.ref,
                    "DueDate": invoice.invoice_date_due.strftime('%Y-%m-%d'),
                    "InvoiceDate": invoice.invoice_date.strftime('%Y-%m-%d'),
                    "InvoiceRows": InvoiceRows,
                    "InvoiceType": "INVOICE",
                    "Language": "SV",
                    "Remarks": "",
                    }
                })
            r = json.loads(r)
            if r.get('ErrorInformation'):
                invoice._message_log(body='Error Creating Invoice Fortnox %s ' % r['ErrorInformation']['message'], subject='Fortnox Error')
                _logger.error('%s has prolem in its contact information, please check it' % invoice.partner_id.name)
            else:
                invoice.ref = r["Invoice"]["CustomerNumber"]
                invoice.name = r["Invoice"]["DocumentNumber"]
                invoice.is_move_sent = True

class AccountInvoiceSend(models.TransientModel):
    _inherit = 'account.invoice.send'
    is_fortnox = fields.Boolean(string='Fortnox', default=True)

    def send_and_print_action(self):
        """
        Override normal send_and_print_action with additional
        functionality for fortnox.
        """
        res = super(AccountInvoiceSend, self).send_and_print_action()
        if self.is_fortnox:
            for invoice in self.invoice_ids:
                invoice.remove_zero_cost_lines()
                invoice.fortnox_create()
                # Do not spam fortnox
                time.sleep(1)
        return res
