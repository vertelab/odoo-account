import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError

_logger = logging.getLogger(__name__)

class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    user_id = fields.Many2one(comodel_name="res.users")
    user_boss_id = fields.Many2one(comodel_name="res.users")

    @api.onchange("user_id")
    def set_boss(self):
        if self.user_id and self.user_id.employee_id and self.user_id.employee_id.parent_id and self.user_id.employee_id.parent_id.user_partner_id and self.user_id.employee_id.parent_id.user_partner_id.user_id:
            self.user_boss_id = self.user_id.employee_id.parent_id.user_partner_id.user_id.id


