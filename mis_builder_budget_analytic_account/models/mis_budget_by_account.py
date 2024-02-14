# Copyright 2017-2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api

SRC_MIS_BUDGET_BY_ANALYTIC_ACCOUNT = "mis_budget_by_analytic_account"


class MisBudgetByAnalyticAccount(models.Model):
    _name = "mis.budget.by.analytic.account"
    _description = "MIS Budget by Analytic Account"
    _inherit = ["mis.budget.abstract", "mail.thread"]

    item_ids = fields.One2many(
        comodel_name="mis.budget.by.analytic.account.item", inverse_name="budget_id", copy=True
    )
    company_id = fields.Many2one(required=True)
    allow_items_overlap = fields.Boolean(
        help="If checked, overlap between budget items is allowed"
    )


class MisReportInstancePeriod(models.Model):
    _inherit = "mis.report.instance.period"

    source = fields.Selection(
        selection_add=[
            (SRC_MIS_BUDGET_BY_ANALYTIC_ACCOUNT, "MIS Budget by Analytic Account"),
        ],
        ondelete={
            SRC_MIS_BUDGET_BY_ANALYTIC_ACCOUNT: "cascade",
        },
    )
    source_mis_budget_by_analytic_account_id = fields.Many2one(
        comodel_name="mis.budget.by.analytic.account", string="Budget by Analytic Account"
    )

    @api.depends("source")
    def _compute_source_aml_model_id(self):
        for record in self:
            if record.source == SRC_MIS_BUDGET_BY_ANALYTIC_ACCOUNT:
                record.source_aml_model_id = (
                    self.env["ir.model"]
                    .sudo()
                    .search([("model", "=", "mis.budget.by.analytic.account.item")])
                )
        return super()._compute_source_aml_model_id()

    def _get_additional_move_line_filter(self):
        domain = super()._get_additional_move_line_filter()
        if self.source == SRC_MIS_BUDGET_BY_ANALYTIC_ACCOUNT:
            domain.extend([("budget_id", "=", self.source_mis_budget_by_analytic_account_id.id)])
        return domain


class MisReportInstance(models.Model):
    _inherit = "mis.report.instance"

    def _add_column(self, aep, kpi_matrix, period, label, description):
        if period.source == SRC_MIS_BUDGET_BY_ANALYTIC_ACCOUNT:
            return self._add_column_move_lines(
                aep, kpi_matrix, period, label, description
            )
        else:
            return super()._add_column(aep, kpi_matrix, period, label, description)