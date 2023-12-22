from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResBank(models.Model):
    _inherit = "res.bank"

    # openbanking_integration_id = fields.One2many('res.partner')
