# Copyright 2017-2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MisBudgetByAnalyticAccountItem(models.Model):
    _inherit = ["mis.budget.item.abstract", "prorata.read_group.mixin"]
    _name = "mis.budget.by.analytic.account.item"
    _description = "MIS Budget Item (by Analytic Account)"
    _order = "budget_id, date_from, analytic_account_id"

    name = fields.Char(string="Label")
    budget_id = fields.Many2one(comodel_name="mis.budget.by.analytic.account")
    debit = fields.Monetary(default=0.0, currency_field="company_currency_id")
    credit = fields.Monetary(default=0.0, currency_field="company_currency_id")
    balance = fields.Monetary(
        compute="_compute_balance",
        inverse="_inverse_balance",
        store=True,
        currency_field="company_currency_id",
    )
    company_id = fields.Many2one(
        "res.company",
        related="budget_id.company_id",
        readonly=True,
        store=True,
    )
    company_currency_id = fields.Many2one(
        "res.currency",
        related="budget_id.company_id.currency_id",
        string="Company Currency",
        readonly=True,
        help="Utility field to express amount currency",
        store=True,
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Analytic Account",
        required=True,
        # TODO domain (company_id)
    )

    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Account",
        required=True,
        # TODO domain (company_id)
    )

    _sql_constraints = [
        (
            "credit_debit1",
            "CHECK (credit*debit=0)",
            "Wrong credit or debit value in budget item! "
            "Credit or debit should be zero.",
        ),
        (
            "credit_debit2",
            "CHECK (credit+debit>=0)",
            "Wrong credit or debit value in budget item! "
            "Credit and debit should be positive.",
        ),
    ]

    @api.depends("debit", "credit")
    def _compute_balance(self):
        for rec in self:
            rec.balance = rec.debit - rec.credit

    def _prepare_overlap_domain(self):
        """Prepare a domain to check for overlapping budget items."""
        if self.budget_id.allow_items_overlap:
            # Trick mis.budget.abstract._check_dates into never seeing
            # overlapping budget items. This "hack" is necessary because, for now,
            # overlapping budget items is only possible for budget by account items
            # and kpi budget items.
            return [("id", "=", 0)]
        domain = super()._prepare_overlap_domain()
        domain.extend([("analytic_account_id", "=", self.analytic_account_id.id)])
        return domain

    @api.constrains(
        "date_range_id",
        "date_from",
        "date_to",
        "budget_id",
        "analytic_account_id",
    )
    def _check_dates(self):
        super()._check_dates()
        return

    def _inverse_balance(self):
        for rec in self:
            if rec.balance < 0:
                rec.credit = -rec.balance
                rec.debit = 0
            else:
                rec.credit = 0
                rec.debit = rec.balance

    @api.depends("date_from", "date_to", 'analytic_account_id')
    def _compute_actual_amount(self):
        for rec in self:
            if (rec.date_from or rec.date_to) and rec.analytic_account_id:
                count, actual_amount = self._get_analytic_amount(rec.analytic_account_id, rec.date_from, rec.date_to)
                rec.actual_amount = actual_amount
                rec.analytic_line_count = count
            else:
                rec.actual_amount = 0
                rec.analytic_line_count = 0

    actual_amount = fields.Float(string="Actual Amount", compute=_compute_actual_amount)
    analytic_line_count = fields.Float(string="Analytic Line Count", compute=_compute_actual_amount)

    def _get_analytic_amount(self, account_id, date_from, date_to):
        analytic_line_ids = self.env['account.analytic.line'].search([
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('account_id', '=', account_id.id),
        ])
        return len(analytic_line_ids), sum(analytic_line_ids.mapped('amount'))

    def action_read_budget_by_analytic_account(self):
        self.ensure_one()
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mis.budget.by.analytic.account.item',
            'res_id': self.id,
        }

    def action_view_analytic_account_item(self):
        self.ensure_one()
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'tree',
            'view_mode': 'tree',
            'res_model': 'account.analytic.line',
            'domain': [
                ('account_id', '=', self.analytic_account_id.id),
                ('date', '>=', self.date_from), ('date', '<=', self.date_to)
            ]
        }
