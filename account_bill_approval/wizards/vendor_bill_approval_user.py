# Copyright 2026 Vertel Sverige AB
# SPDX-License-Identifier: AGPL-3
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class VendorBillApprovalUser(models.TransientModel):
    _name = "vendor.bill.approval.user"
    _description = "Send Vendor Bill Approval Request"

    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Bill",
        required=True,
        ondelete="cascade",
    )
    line_ids = fields.Many2many(
        comodel_name="bill.approval.user.line",
        string="Approvers To Notify",
        compute="_compute_line_ids",
        readonly=False,
    )

    @api.depends("move_id")
    def _compute_line_ids(self):
        for wizard in self:
            wizard.line_ids = wizard.move_id.approving_user_ids.filtered(
                lambda line: line.state in ("new", "rejected")
            )

    def action_send(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Select at least one approver to notify."))
        # Defence in depth: the view restricts ``line_ids`` to this bill's
        # own pending lines, but a crafted RPC call could still pass foreign
        # ids. Never send an approval request for another bill's line.
        foreign = self.line_ids.filtered(
            lambda line: line.move_id != self.move_id
        )
        if foreign:
            raise UserError(_(
                "The following approvers do not belong to this bill: %s",
                ", ".join(foreign.mapped("user_id.display_name")),
            ))
        self.line_ids.action_send_request()
        # Closing the wizard does not refresh the bill form behind it, so
        # the stored computed ``bill_approval_state`` would keep showing its
        # previous value. Reload the underlying record as well.
        return {
            "type": "ir.actions.act_window_close",
            "infos": {"bill_approval_refresh": True},
        }
