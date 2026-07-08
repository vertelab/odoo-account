"""Account Balance — standalone model for fiscal year balances.

No inheritance from mis.budget.abstract — this is a simple data container.
"""

from odoo import api, fields, models


class AccountBalance(models.Model):
    _name = "account.balance"
    _description = "Account Balance"
    _order = "fiscalyear_id, account_id"

    fiscalyear_id = fields.Many2one(
        "account.fiscal.year",
        string="Fiscal Year",
        required=True,
        ondelete="cascade",
        index=True,
    )
    account_id = fields.Many2one(
        "account.account",
        string="Account",
        required=True,
        ondelete="cascade",
    )
    debit = fields.Monetary(
        string="Debit",
        default=0.0,
        currency_field="currency_id",
    )
    credit = fields.Monetary(
        string="Credit",
        default=0.0,
        currency_field="currency_id",
    )
    balance = fields.Monetary(
        string="Balance",
        compute="_compute_balance",
        store=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    @api.depends("debit", "credit")
    def _compute_balance(self):
        for rec in self:
            rec.balance = rec.debit - rec.credit
