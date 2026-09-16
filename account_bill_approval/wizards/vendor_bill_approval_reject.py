# Copyright 2026 Vertel AB
# SPDX-License-Identifier: AGPL-3
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class VendorBillApprovalReject(models.TransientModel):
    _name = "vendor.bill.approval.reject"
    _description = "Reject Vendor Bill"

    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Bill",
        required=True,
        ondelete="cascade",
    )
    line_id = fields.Many2one(
        comodel_name="bill.approval.user.line",
        string="Approval Line",
        required=True,
        ondelete="cascade",
    )
    reason = fields.Text(string="Reason", required=True)

    @api.onchange("move_id")
    def _onchange_move_id(self):
        for wizard in self:
            if wizard.move_id:
                wizard.line_id = wizard.move_id.approving_user_ids.filtered(
                    lambda line: line.user_id == self.env.user
                    and line.state == "request"
                )[:1]

    def action_reject(self):
        self.ensure_one()
        if not self.reason or not self.reason.strip():
            raise UserError(_("A reason is required when rejecting a bill."))
        self.line_id.action_reject(reason=self.reason)
        return {"type": "ir.actions.act_window_close"}
