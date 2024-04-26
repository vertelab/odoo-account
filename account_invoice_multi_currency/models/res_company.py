from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    invoice_multi_currency_ids = fields.Many2many('res.currency',
                                                  string='Invoice Currencies')
