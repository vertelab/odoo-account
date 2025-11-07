from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountMove(models. Model):
    _inherit = 'account.move'

    def action_post(self):
        if any(state == 'closed' for state in self.line_ids.mapped('account_id').mapped('state')):
            raise UserError("You have one or more account that is closed.")

        return super().action_post()