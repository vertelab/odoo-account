
import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def open2generated(self):
        context_copy = self.env.context.copy()
        context_copy.update({'check_move_period_validity': False})
        res = super(AccountPaymentOrder, self).open2generated()
        move_ids = self.payment_line_ids.mapped('move_line_id.move_id').filtered(
            lambda move: move.payment_state == 'not_paid'
        )
        move_ids.with_context(context_copy).write({'payment_state': 'in_payment'})
        return res
        
        
    def action_cancel(self):
        context_copy = self.env.context.copy()
        context_copy.update({'check_move_period_validity': False})
        res = super(AccountPaymentOrder, self).action_cancel()
        
        move_ids = self.payment_line_ids.mapped('move_line_id.move_id').filtered(
            lambda move: move.payment_state == 'in_payment'
        )
        move_ids.with_context(context_copy).write({'payment_state': 'not_paid'})
        return res

