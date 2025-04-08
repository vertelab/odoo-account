from odoo import api, fields, models, _
from odoo.osv.expression import AND
from odoo.exceptions import ValidationError
from odoo.addons.mis_builder_budget.models.mis_report_instance_period import SRC_MIS_BUDGET, SRC_MIS_BUDGET_BY_ACCOUNT
from odoo.addons.mis_builder_budget.models.mis_report_instance import MisBudgetAwareExpressionEvaluator


class MisReportInstance(models.Model):
    _inherit = 'mis.report.instance'

    @api.depends('move_lines_source')
    def _compute_account_model_depricated(self):
        for record in self:
            if record.move_lines_source.model == 'mis.budget.by.analytic.account.item':
                record.account_model = (
                    record.move_lines_source.sudo()
                    .field_id.filtered(lambda r: r.name == "analytic_account_id")
                    .relation
                )
            else:
                record.account_model = (
                    record.move_lines_source.sudo()
                    .field_id.filtered(lambda r: r.name == "account_id")
                    .relation
                )

    def _add_column(self, aep, kpi_matrix, period, label, description):
        if period.source == "mis_budget_by_analytic_account":
            return self._add_column_budget_analytic_items(
                aep, kpi_matrix, period, label, description
            )
        else:
            return super()._add_column(aep, kpi_matrix, period, label, description)

    def drilldown(self, arg):
        self.ensure_one()
        period_id = arg.get("period_id")
        if period_id:
            period = self.env["mis.report.instance.period"].browse(period_id)
            if period.source == SRC_MIS_BUDGET:
                expr_id = arg.get("expr_id")
                if not expr_id:
                    return False
                domain = [
                    ("date_from", "<=", period.date_to),
                    ("date_to", ">=", period.date_from),
                    ("kpi_expression_id", "=", expr_id),
                    ("budget_id", "=", period.source_mis_budget_id.id),
                ]
                domain.extend(period._get_additional_budget_item_filter())
                return {
                    "name": period.name,
                    "domain": domain,
                    "type": "ir.actions.act_window",
                    "res_model": "mis.budget.item",
                    "views": [[False, "list"], [False, "form"]],
                    "view_mode": "list",
                    "target": "current",
                }
        return super().drilldown(arg)
