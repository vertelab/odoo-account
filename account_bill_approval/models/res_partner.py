# Copyright 2026 Vertel AB
# SPDX-License-Identifier: AGPL-3
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    bill_approving_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="res_partner_bill_approvers_rel",
        column1="partner_id",
        column2="user_id",
        string="Default Bill Approvers",
        help="Suggested approvers for this vendor. They are pre-filled on "
             "new vendor bills but can always be changed on the bill.",
    )
    bill_approval_manager_user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Bill Approval Managers",
        compute="_compute_bill_approval_manager_user_ids",
        help="Technical field: users allowed to configure approvers.",
    )

    @api.depends_context("uid")
    def _compute_bill_approval_manager_user_ids(self):
        managers = self.env.user.bill_approval_manager_user_ids
        for partner in self:
            partner.bill_approval_manager_user_ids = managers

    def write(self, vals):
        """Only Bill Approval / Manager may change the default approvers.

        The view already renders the field read-only, but RPC calls can
        bypass that, so the rule is enforced here as well.
        """
        if (
            "bill_approving_user_ids" in vals
            and not self.env.su
            and not self.env.user.has_group(
                "account_bill_approval.group_bill_approval_manager"
            )
        ):
            raise UserError(_(
                "Only users with the 'Bill Approval / Manager' right can "
                "change the default approvers of a vendor."
            ))
        return super().write(vals)
