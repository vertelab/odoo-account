# Copyright 2026 Vertel AB
# SPDX-License-Identifier: AGPL-3
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    bill_approval_manager_user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Bill Approval Managers",
        compute="_compute_bill_approval_manager_user_ids",
        help="Users in the Bill Approval / Manager group. Exposed so views "
             "can make the approver fields read-only for everyone else.",
    )

    @api.depends_context("uid")
    def _compute_bill_approval_manager_user_ids(self):
        group = self.env.ref(
            "account_bill_approval.group_bill_approval_manager",
            raise_if_not_found=False,
        )
        managers = group.users if group else self.env["res.users"]
        for user in self:
            user.bill_approval_manager_user_ids = managers

    @api.model
    def _bill_approval_is_manager(self):
        """Whether the current user may configure approvers."""
        return self.env.user.has_group(
            "account_bill_approval.group_bill_approval_manager"
        )

    @api.model
    def _bill_approval_user_domain(self):
        """Users allowed to be picked as bill approvers.

        Restricted to the 'Bill Approver' group. The restriction is
        required for symmetry: the reject wizard is gated on that group,
        so an approver outside it could approve but never reject. The
        pickers apply this domain through the ``filter_bill_approval_user``
        context key, and ``action_approve``/``action_reject`` enforce it
        again on the line itself.

        Returns a domain, or ``None`` when the group does not exist.
        """
        group = self.env.ref(
            "account_bill_approval.group_bill_approval_user",
            raise_if_not_found=False,
        )
        if not group:
            return None
        return [("id", "in", group.users.ids)]

    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        """Support the ``filter_bill_approval_user`` context key.

        The approver pickers set this key, so only members of the
        'Bill Approver' group are offered. It stays opt-in: callers that
        do not ask for it see every user.
        """
        if self.env.context.get("filter_bill_approval_user"):
            domain = self._bill_approval_user_domain()
            if domain:
                args = list(args) + domain
        return super().search(args, offset=offset, limit=limit, order=order)

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = list(args or [])
        if self.env.context.get("filter_bill_approval_user"):
            domain = self._bill_approval_user_domain()
            if domain:
                args += domain
        return super().name_search(name, args, operator, limit)
