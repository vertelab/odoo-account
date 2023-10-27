from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    red_invoice_terms = fields.Text(related='company_id.red_invoice_terms', string="Terms & Conditions with red text", readonly=False)


