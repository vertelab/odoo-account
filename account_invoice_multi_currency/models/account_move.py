from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_multi_currency_ids = fields.Many2many('res.currency',
                                                  string='Invoice Currencies',
                                                  related='company_id.invoice_multi_currency_ids')
