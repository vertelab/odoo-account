from locale import currency
from odoo import _, api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    exclude_from_payment = fields.Boolean(string="Exclude From Payment")