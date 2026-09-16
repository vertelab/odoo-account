# Copyright 2026 Vertel AB
# SPDX-License-Identifier: AGPL-3
from odoo import fields, models


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
