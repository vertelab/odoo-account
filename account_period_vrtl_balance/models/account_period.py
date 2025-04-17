import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class AccountPeriod(models.Model):
    _inherit = 'account.period'
    _description = 'Account Period with Balance Fields'

    incoming_balance = fields.Float(string="Incoming Balance", compute="_compute_balance")
    outgoing_balance = fields.Float(string="Outgoing Balance", compute="_compute_balance")

    @api.depends('date_stop')
    def _compute_balance(self):
        for record in self:
            # Sum of posted customer invoices before this period's stop date
            incoming_invoices = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date', '<', record.date_stop)
            ])
            record.incoming_balance = sum(incoming_invoices.mapped("amount_total"))

            # Sum of posted customer invoices up to and including this period's stop date
            outgoing_invoices = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date', '<=', record.date_stop)
            ])
            record.outgoing_balance = sum(outgoing_invoices.mapped("amount_total"))
