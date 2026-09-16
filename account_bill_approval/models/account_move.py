# Copyright 2026 Vertel AB
# SPDX-License-Identifier: AGPL-3
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

BILL_MOVE_TYPES = ("in_invoice", "in_refund")

MOVE_TYPE_LABELS = {
    "entry": "Journal Entry",
    "out_invoice": "Customer Invoice",
    "out_refund": "Customer Credit Note",
    "in_invoice": "Vendor Bill",
    "in_refund": "Vendor Credit Note",
    "out_receipt": "Sales Receipt",
    "in_receipt": "Purchase Receipt",
}


class AccountMove(models.Model):
    _inherit = "account.move"

    approving_user_ids = fields.One2many(
        comodel_name="bill.approval.user.line",
        inverse_name="move_id",
        string="Approvers",
        copy=True,
    )
    bill_approval_state = fields.Selection(
        selection=[
            ("none", "No Approvers"),
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Approval Status",
        compute="_compute_bill_approval_state",
        store=True,
        tracking=True,
    )
    to_approve = fields.Boolean(
        string="Waiting For My Approval",
        compute="_compute_to_approve",
        search="_search_to_approve",
        help="True when the current user still has to approve this bill.",
    )
    approver_check_ok = fields.Boolean(
        string="Has Approvers",
        compute="_compute_bill_approval_state",
        store=True,
    )
    invoice_approved_check = fields.Boolean(
        string="Bill Approved",
        compute="_compute_bill_approval_state",
        store=True,
        tracking=True,
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends(
        "approving_user_ids",
        "approving_user_ids.state",
        "move_type",
    )
    def _compute_bill_approval_state(self):
        for move in self:
            lines = move.approving_user_ids
            move.approver_check_ok = bool(lines)
            if not lines:
                move.bill_approval_state = "none"
                move.invoice_approved_check = False
                continue
            states = set(lines.mapped("state"))
            if "rejected" in states:
                move.bill_approval_state = "rejected"
                move.invoice_approved_check = False
            elif states <= {"done"}:
                move.bill_approval_state = "approved"
                move.invoice_approved_check = True
            else:
                move.bill_approval_state = "pending"
                move.invoice_approved_check = False

    @api.depends("approving_user_ids", "approving_user_ids.state", "approving_user_ids.user_id")
    def _compute_to_approve(self):
        for move in self:
            move.to_approve = bool(move.approving_user_ids.filtered(
                lambda line: line.state == "request"
                and line.user_id == self.env.user
            ))

    def _search_to_approve(self, operator, value):
        """Make ``to_approve`` searchable.

        The field depends on the current user, so it cannot be stored.
        Instead we translate the domain into a search on the approval
        lines and return the matching bill ids.
        """
        if operator not in ("=", "!="):
            raise UserError(_(
                "Unsupported operator %(op)s for 'Waiting For My Approval'.",
                op=operator,
            ))
        if isinstance(value, str):
            value = value.lower() in ("true", "1")
        positive = (operator == "=") == bool(value)

        lines = self.env["bill.approval.user.line"].search([
            ("user_id", "=", self.env.user.id),
            ("state", "=", "request"),
        ])
        move_ids = lines.mapped("move_id").ids
        return [("id", "in" if positive else "not in", move_ids)]

    # ------------------------------------------------------------------
    # Onchange — approvers are freely selectable (T/11311)
    # ------------------------------------------------------------------
    @api.onchange("partner_id")
    def onchange_partner_set_approvers(self):
        """Pre-fill approvers from the vendor, but never lock the field.

        The vendor's ``bill_approving_user_ids`` is only a *suggestion*:
        the user may add or remove approvers on the bill itself.
        """
        for move in self:
            if move.move_type not in BILL_MOVE_TYPES:
                continue
            # Drop only untouched, not-yet-requested lines coming from a
            # previous vendor selection; keep anything the user acted on.
            stale = move.approving_user_ids.filtered(
                lambda line: line.state == "new"
            )
            if stale:
                move.approving_user_ids = [(3, line.id) for line in stale]
            if not move.partner_id:
                continue
            new_lines = []
            for user in move.partner_id.bill_approving_user_ids:
                if user in move.approving_user_ids.mapped("user_id"):
                    continue
                new_lines.append((0, 0, {"user_id": user.id, "state": "new"}))
            if new_lines:
                move.approving_user_ids = new_lines

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _bill_approval_label(self):
        self.ensure_one()
        return MOVE_TYPE_LABELS.get(self.move_type, self.move_type)

    def _bill_approval_notify(self, line):
        """Send the approval request mail to one approver."""
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param(
            "web.base.url", ""
        )
        body = _(
            "Hello %(name)s,<br/><br/>"
            "Please approve the <a href='%(url)s'>vendor bill</a>.<br/><br/>",
            name=line.user_id.name,
            url=self._bill_approval_access_url(base_url),
        )
        mail = self.env["mail.mail"].sudo().create({
            "recipient_ids": [(4, line.user_id.partner_id.id)],
            "subject": _("%s - Vendor Bill Approval Request") % self.env.company.name,
            "body_html": body,
        })
        mail.send()
        self.message_post(body=_(
            "%(bill)s approval request has been sent to %(user)s.",
            bill=self._bill_approval_label(),
            user=line.user_id.name,
        ))

    def _bill_approval_access_url(self, base_url=None):
        self.ensure_one()
        if base_url is None:
            base_url = self.env["ir.config_parameter"].sudo().get_param(
                "web.base.url", ""
            )
        return "%s/odoo/action-account.action_move_in_invoice_type/%s" % (
            base_url.rstrip("/"), self.id,
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_request_bill_approval(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "vendor.bill.approval.user",
            "name": _("Send Vendor Bill Approval Request"),
            "view_mode": "form",
            "target": "new",
            "context": {"default_move_id": self.id},
        }

    def action_user_approve_bill(self):
        for move in self:
            line = move.approving_user_ids.filtered(
                lambda rec: rec.user_id == self.env.user
                and rec.state == "request"
            )
            if not line:
                raise ValidationError(_(
                    "You have no pending approval on this bill."
                ))
            line.action_approve()
        return True

    def action_user_reject_bill(self):
        self.ensure_one()
        line = self.approving_user_ids.filtered(
            lambda rec: rec.user_id == self.env.user
            and rec.state == "request"
        )
        if not line:
            raise ValidationError(_(
                "You have no pending approval on this bill."
            ))
        return {
            "type": "ir.actions.act_window",
            "res_model": "vendor.bill.approval.reject",
            "name": _("Reject Vendor Bill"),
            "view_mode": "form",
            "target": "new",
            "context": {"default_move_id": self.id, "default_line_id": line.id},
        }

    def action_post(self):
        """Block posting while approvals are outstanding."""
        for move in self.filtered(lambda mv: mv.move_type in BILL_MOVE_TYPES):
            pending = move.approving_user_ids.filtered(
                lambda line: line.state in ("new", "request", "rejected")
            )
            if pending:
                raise ValidationError(_(
                    "All approvers must approve the bill before it can be "
                    "confirmed. Outstanding: %s",
                    ", ".join(pending.mapped("user_id.display_name")),
                ))
        return super().action_post()
