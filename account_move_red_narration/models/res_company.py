from odoo import api, fields, models, _
from odoo.exceptions import ValidationError



class ResCompany(models.Model):
    _inherit = "res.company"
    
    red_invoice_terms = fields.Text(string='Default Terms and Conditions', translate=True)
