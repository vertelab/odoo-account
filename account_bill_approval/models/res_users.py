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

        Returns a domain, or ``None`` when no restriction applies.
        The group is intentionally *not* required: any user may be an
        approver, the group only marks the default pool.
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
        """Support the legacy ``filter_bill_approval_user`` context key.

        Unlike the legacy module this filter is *opt-in*: it is only
        applied when the caller explicitly asks for it, so approvers can
        be selected freely by default (T/11311).
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
