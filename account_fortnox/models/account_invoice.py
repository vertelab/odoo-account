1  # -*- coding: utf-8 -*-
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
        print(fortnox_values)
        final_pay_date_string = fortnox_values.get('FinalPayDate')
        final_pay_date = datetime.strptime(final_pay_date_string, '%Y-%m-%d').date()
        fortnox_journal = self.env['account.journal'].search([('name', 'like', 'fortnox'), ('type', '=', 'bank')])

        if not fortnox_journal:
            raise UserError(
                "No valid Journal found. Create a journal called something containing fortnox and of the type bank.")
        elif len(fortnox_journal) > 1:
            raise UserError(
                "More than one valid journal found for fortnox. Make sure there is only one journal of the type Bank "
                "with fortnox in its name.")
        for rec in self:
            payment_register_params = dict(
                amount=rec.amount_residual,
                communication=rec.payment_reference,
                currency_id=rec.currency_id.id,
                journal_id=fortnox_journal.id,
                payment_date=final_pay_date if final_pay_date else rec.date,
                payment_type=rec.amount_residual > 0 and 'inbound' or 'outbound',
                partner_id=rec.partner_id.id,
                partner_bank_id=fortnox_journal.bank_account_id.id,
            )

            payment_id = self.env['account.payment.register'].with_context(
                active_model='account.move',
                active_ids=rec.id,
            ).create(payment_register_params)
            payment_id.action_create_payments()

    def _reverse_invoice(self, invoice_id, credit_invoice_ref, company_id):
        # Refund the invoice
        wiz_context = {
            'active_model': 'account.move',
            'active_ids': [invoice_id.id],
            'default_journal_id': invoice_id.journal_id
        }
        refund_invoice_wiz = self.env['account.move.reversal'].with_context(wiz_context).create({
            'refund_method': 'refund',
            'date': fields.Date.today(),
        })

        refund_invoice = self.env['account.move'].browse(refund_invoice_wiz.reverse_moves()['res_id'])
        refund_invoice.action_post()
        refund_invoice.name = credit_invoice_ref
        refund_invoice.fortnox_response = company_id.fortnox_request(
            "GET", f"{BASE_URL}/3/invoices/{credit_invoice_ref}"
        )

        (invoice_id + refund_invoice).line_ids \
            .filtered(lambda line: line.account_type in ('asset_receivable', 'liability_payable')) \
            .reconcile()

    def update_invoice_status_fortnox_cron(self):
        from_date = datetime.now() - timedelta(days=365)
        for company_id in self.env['res.company'].search([]):
            move_id = self.env['account.move'].search([
                ('company_id', '=', company_id.id),
                ('create_date', '>', from_date),
                ('payment_state', 'not in', ['paid','reversed','partially_paid']),
                ('state', '!=', 'draft'),
                ('state', '!=', 'cancel'),
                ('move_type', '=', 'out_invoice')
            ])
            for invoice in move_id:
                fortnox_res = company_id.fortnox_request(
                    "GET",
                    f"{BASE_URL}/3/invoices/{invoice.id}"
                )

                if fortnox_res.get('ErrorInformation', {}).get('Code'):
                    pass
                elif invoice_info := fortnox_res.get('Invoice'):
                    credit_invoice_ref = int(invoice_info.get('CreditInvoiceReference'))
                    if credit_invoice_ref > 0:
                        invoice._reverse_invoice(
                            invoice_id=invoice, credit_invoice_ref=credit_invoice_ref, company_id=company_id
                        )
                    elif credit_invoice_ref == 0 and invoice.state == 'posted':
                        invoice.update_invoice_status_fortnox_paid(invoice_info)

                invoice.fortnox_response = fortnox_res

    def sync_fortnox(self):
        invoice_id = self.env['account.move'].browse(self.id)

        fortnox_res = self.company_id.fortnox_request(
            "get",
            f"{BASE_URL}/3/invoices/{invoice_id.id}"
        )

        if fortnox_invoice := fortnox_res.get('Invoice'):
            self.fortnox_update(invoice_id, fortnox_invoice)
        elif fortnox_res.get('ErrorInformation', {}).get('Code') == 2000434:
            self.fortnox_create(invoice_id)

    def fortnox_update(self, invoice, fortnox_invoice):
        invoice.ref = fortnox_invoice["CustomerNumber"]
        invoice.name = fortnox_invoice["DocumentNumber"]
        invoice.partner_id.ref = fortnox_invoice["CustomerNumber"]
        invoice.is_move_sent = True

    def fortnox_create(self, invoice):
        if not invoice.invoice_date_due:
            raise UserError(_("ERROR: missing date_due on invoice."))
        if not invoice.partner_id.commercial_partner_id.ref:
            invoice.partner_id.partner_create()
        if invoice.partner_id.commercial_partner_id.ref:
            invoice.partner_id.partner_update()

        invoice_lines = []

        for line in invoice.invoice_line_ids:
            if line.product_id:
                line_name = line.name.split(' ')[1] \
                    if len(line.name.split(' ')) == 2 \
                    else line.name.replace('[', '').replace(']', '').strip(' ')

                line.product_id.article_update()

                invoice_lines.append({
                    "AccountNumber": line.account_id.code,
                    "DeliveredQuantity": line.quantity,
                    "Description": line_name,
                    "ArticleNumber": line.product_id.default_code if line.product_id else None,
                    "Price": line.price_unit,
                    "VAT": int(line.tax_ids.mapped('amount')[0]) if len(line.tax_ids) > 0 else None,
                })

        r = self.company_id.fortnox_request(
            'POST',
            "https://api.fortnox.se/3/invoices",
            data={"Invoice": {
                "Comments": "",
                "Currency": "SEK",
                "CustomerName": invoice.partner_id.commercial_partner_id.name,
                "CustomerNumber": invoice.partner_id.commercial_partner_id.ref,
                "DueDate": invoice.invoice_date_due.strftime('%Y-%m-%d'),
                "DocumentNumber": invoice.id,  # <-- invoice can only contain numbers apparently
                "InvoiceDate": invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else fields.Date.today().strftime('%Y-%m-%d'),
                "InvoiceRows": invoice_lines,
                "InvoiceType": "INVOICE",
                "Language": "SV",
                "Remarks": "",
            }
        })

        if r.get('ErrorInformation'):
            invoice._message_log(
                body='Error Creating Invoice Fortnox %s ' % r['ErrorInformation']['message'],
                subject='Fortnox Error'
            )
            _logger.error('%s has problem in its contact information, please check it' % invoice.partner_id.name)
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
                invoice.sync_fortnox()
                # Do not spam fortnox
                time.sleep(1)
        return res
