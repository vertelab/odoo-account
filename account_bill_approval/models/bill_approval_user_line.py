# Copyright 2026 Vertel AB
# SPDX-License-Identifier: AGPL-3
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BillApprovalUserLine(models.Model):
    """One approval step on a vendor bill.

    Kept model/field names compatible with the legacy Linserv module
    (``purchase_vendor_bill_approval``) so that existing data can be
    reused without migration of the relation itself.
    """

    _name = "bill.approval.user.line"
    _description = "Bill Approver"
    _order = "move_id, id"
    _rec_name = "user_id"

    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Related Bill",
        ondelete="cascade",
        required=True,
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Approver",
        required=True,
        ondelete="restrict",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        related="move_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    state = fields.Selection(
        selection=[
            ("new", "New"),
            ("request", "Requested"),
            ("done", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        default="new",
        required=True,
        index=True,
    )
    date_requested = fields.Datetime(string="Requested On", readonly=True)
    date_approved = fields.Datetime(string="Approved On", readonly=True)
    date_rejected = fields.Datetime(string="Rejected On", readonly=True)
    rejected_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Rejected By",
        readonly=True,
        ondelete="restrict",
    )
    reject_reason = fields.Text(string="Rejection Reason", readonly=True)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("move_id", "user_id")
    def _check_unique_approver(self):
        for line in self:
            if not line.move_id or not line.user_id:
                continue
            duplicate = self.search_count([
                ("id", "!=", line.id),
                ("move_id", "=", line.move_id.id),
                ("user_id", "=", line.user_id.id),
            ])
            if duplicate:
                raise ValidationError(_(
                    "%(user)s is already listed as an approver on %(bill)s.",
                    user=line.user_id.display_name,
                    bill=line.move_id.display_name,
                ))

    # ------------------------------------------------------------------
    # Business methods
    # ------------------------------------------------------------------
    def action_send_request(self):
        """Notify the approver and move the line to *Requested*."""
        for line in self:
            if line.state not in ("new", "rejected"):
                raise UserError(_(
                    "Only lines in state New or Rejected can be requested "
                    "for approval (line is %(state)s).",
                    state=line.state,
                ))
            line.move_id._bill_approval_notify(line)
            line.write({
                "state": "request",
                "date_requested": fields.Datetime.now(),
            })
        return True

    def action_approve(self):
        """Approve the bill on behalf of the current user."""
        for line in self:
            if line.user_id != self.env.user:
                raise UserError(_(
                    "You are not allowed to approve this bill. "
                    "It is assigned to %s.",
                    line.user_id.display_name,
                ))
            if line.state != "request":
                raise UserError(_(
                    "Only requested approvals can be approved "
                    "(line is %(state)s).",
                    state=line.state,
                ))
            line.write({
                "state": "done",
                "date_approved": fields.Datetime.now(),
            })
            line.move_id._bill_approval_log(_(
                "%(bill)s has been approved by %(user)s.",
                bill=line.move_id._bill_approval_label(),
                user=self.env.user.display_name,
            ))
        return True

    def action_reject(self, reason=None):
        """Reject the bill (Väg B: reject and reopen).

        The rejecting user is blocked from approving the same line again;
        a new approval line has to be added instead.
        """
        for line in self:
            if line.user_id != self.env.user:
                raise UserError(_(
                    "You are not allowed to reject this bill. "
                    "It is assigned to %s.",
                    line.user_id.display_name,
                ))
            if line.state != "request":
                raise UserError(_(
                    "Only requested approvals can be rejected "
                    "(line is %(state)s).",
                    state=line.state,
                ))
            line.write({
                "state": "rejected",
                "date_rejected": fields.Datetime.now(),
                "rejected_by_id": self.env.user.id,
                "reject_reason": reason or _("No reason given."),
            })
            line.move_id._bill_approval_log(_(
                "%(bill)s was rejected by %(user)s. Reason: %(reason)s",
                bill=line.move_id._bill_approval_label(),
                user=self.env.user.display_name,
                reason=reason or _("No reason given."),
            ))
            # Väg B: put the bill back into draft so it can be corrected
            if line.move_id.state == "posted":
                line.move_id.button_draft()
        return True

    def unlink(self):
        for line in self:
            if line.state == "done":
                raise ValidationError(_(
                    "Approved lines cannot be deleted."
                ))
        return super().unlink()

    # ------------------------------------------------------------------
    # Systray helper
    # ------------------------------------------------------------------
    @api.model
    def ret_bill_approval_count(self):
        """Number of bills waiting for the current user's approval.

        Used by the systray "pen" so a user immediately sees how many
        vendor bills are queued for them.

        Runs with sudo because an approver may not have read access to
        account.move itself — the count is an aggregate, not a record
        disclosure.
        """
        return self.sudo().search_count([
            ("user_id", "=", self.env.user.id),
            ("state", "=", "request"),
        ])
