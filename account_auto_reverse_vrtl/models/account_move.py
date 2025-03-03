import logging
from odoo import models, fields, api
_logger = logging.getLogger(__name__)

class AccountMoveExtension(models.Model):
    _inherit = 'account.move'

    auto_reverse_date = fields.Date(string='Auto Reverse Date', help='Date when the journal entry will be automatically reversed')
    reverse_failed = fields.Boolean()
    reverse_reason = fields.Char()

    def _reverse_invoice(self):
        # Refund the invoice
        self.ensure_one()
        wiz_context = {
            'active_model': 'account.move',
            'active_ids': [self.id],
            'default_journal_id': self.journal_id
        }
        #Use the wizard
        refund_invoice_wiz = self.env['account.move.reversal'].with_context(wiz_context).create({
            #'date': fields.Date.today(),
            'date': self.auto_reverse_date
        })

        refund_invoice = self.env['account.move'].browse(refund_invoice_wiz.reverse_moves()['res_id'])
        refund_invoice.action_post()

        #(invoice_id + refund_invoice).line_ids \
        #    .filtered(lambda line: line.account_type in ('asset_receivable', 'liability_payable')) \
        #    .reconcile()


    
    @api.model
    def auto_reverse_invoices(self):
        today = fields.Date.today()
        invoices_to_reverse = self.search([
            ('auto_reverse_date', '<=', today),
            ('state', '=', 'posted'),
            ('payment_state','=','not_paid'),
            ('move_type', 'in', ['out_invoice', 'in_invoice'])
        ])

        for invoice in invoices_to_reverse:
            try:
                invoice._reverse_invoice()
                _logger.info(f"Successfully reversed invoice {invoice.name} (ID: {invoice.id})")
            except Exception as e:
                invoice.reverse_failed = True
                invoice.reverse_reason = e
                _logger.error(f"Failed to reverse invoice {invoice.name} (ID: {invoice.id}). Error: {str(e)}")

        return True
