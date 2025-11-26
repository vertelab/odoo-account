import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError

_logger = logging.getLogger(__name__)

class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    user_id = fields.Many2one(comodel_name="res.users",string="responsible")
    user_boss_id = fields.Many2one(comodel_name="res.users", string="responsible boss",compute="_compute_user_boss_id", store=True)

    def create(self, vals_list):
        user_id = self.env.context.get("uid")
        vals_list.update({"user_id":user_id})
        return super().create(vals_list)

    @api.depends("user_id")
    def _compute_user_boss_id(self):
        for rec in self:
            if rec.user_id and rec.user_id.sudo().employee_parent_id and rec.user_id.sudo().employee_parent_id.user_id:
                rec.user_boss_id = rec.user_id.sudo().employee_parent_id.user_id.id
            else:
                rec.user_boss_id = False