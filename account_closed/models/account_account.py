from odoo import models, fields, api


class AccountAccount(models. Model):
    _inherit = 'account.account'

    state = fields.Selection([('open', 'Open'), ('closed', 'Closed')], default='open', string="State")