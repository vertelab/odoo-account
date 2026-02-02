from odoo import api, fields, models, _
from odoo.exceptions import ValidationError



class ResCompany(models.Model):
    _inherit = "res.company"
    
    important_invoice_narration = fields.Text(string='Important Invoice Narration', translate=True)
