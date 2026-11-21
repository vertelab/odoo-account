from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_multi_currency_ids = fields.Many2many('res.currency',
                                                  string='Invoice Currencies',
                                                  readonly=False,
                                                  related='company_id.invoice_multi_currency_ids')
