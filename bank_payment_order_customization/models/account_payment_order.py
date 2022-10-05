
import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def open2generated(self):
        res = super(AccountPaymentOrder, self).open2generated()
        move_ids = self.payment_line_ids.mapped('move_line_id.move_id').filtered(
            lambda move: move.payment_state == 'not_paid'
        )
        move_ids.write({'payment_state': 'in_payment'})
        return res
