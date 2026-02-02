from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    important_invoice_narration = fields.Text(related='company_id.important_invoice_narration', string="Important Invoice Narration", readonly=False)


