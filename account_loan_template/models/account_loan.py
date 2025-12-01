from odoo import models, fields, api, _

class AccountLoan(models.Model):
    _inherit = 'account.loan'

    account_move_line = fields.Many2one('account.move.line', string="Account Move Line", readonly=True)

