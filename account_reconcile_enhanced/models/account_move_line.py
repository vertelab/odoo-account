# Copyright 2026 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    reconcile_model_id = fields.Many2one(
        comodel_name="account.reconcile.model",
        string="Reconciliation Model",
        copy=False,
        readonly=True,
        help="The reconciliation model that created this journal item.",
    )
