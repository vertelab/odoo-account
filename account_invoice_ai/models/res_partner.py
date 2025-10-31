from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = "res.partner"
    keywords = fields.Char(string="Keywords", help="Use comma to separate keywords unique to this partner")



