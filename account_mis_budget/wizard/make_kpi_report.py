from odoo import api, fields, models, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import logging


class MakeKPIReport(models.TransientModel):
    _name = "make.kpi.report.wizard"
    _description = "Make a kpi report"

    use_last_year = fields.Boolean(default=True)
    factor = fields.Float(default=1)
    date_type = fields.Many2one('date.range.type', string='Date type', required=True)  # Month, Weeks, Every two weeks

    def _mis_report_instance(self, vals):
        mis_report_instance_id = self.env['mis.report.instance'].create(vals)
        return mis_report_instance_id

    def _mis_instance_vals(self, date_range, budget_kpi_id):
        date_from, date_to = self._get_date_(date_range)
        vals = dict(
            report_id=budget_kpi_id.report_id.id,
            name=f'{date_from}--{date_to}',
            date_from=date_from,
            date_to=date_to,
            period_ids=[
                (
                    0,
                    0,
                    dict(
                        name="p1",
                        mode="fix",
                        date_range_id=date_range.id,
                        manual_date_from=date_range.date_start,
                        manual_date_to=date_range.date_end,
                    ),
                )
            ],
        )
        if self.use_last_year and budget_kpi_id.analytic_account_id:
            vals['analytic_domain'] = repr([
                    ('analytic_line_ids.account_id', '=', budget_kpi_id.analytic_account_id.id)
            ])
        return vals

    def action_generate_kpi_report(self):
        budget_kpi_id = self.env['mis.budget'].browse(self._context.get('active_id'))

        date_range_ids = self.date_type.date_range_ids.filtered(
            lambda _date_range: budget_kpi_id.date_from <= _date_range.date_start <= budget_kpi_id.date_to
        )

        for date_range in date_range_ids:
            mis_report_instance = self._mis_report_instance(
                self._mis_instance_vals(date_range=date_range, budget_kpi_id=budget_kpi_id)
            )
            kpi_matrix = mis_report_instance._compute_matrix()

            already_visited = []
            for row in kpi_matrix.iter_rows():
                if row.kpi.id not in already_visited:
                    already_visited.append(row.kpi.id)
                else:
                    continue

                for cell in row.iter_cells():
                    if (isinstance(cell.val, float) and cell.val > 0) or not self.use_last_year:
                        if row.kpi.budgetable:
                            self._mis_budget_item(
                                budget_kpi_id,
                                date_range,
                                row.kpi,
                                cell.val * self.factor if self.use_last_year else 0.0
                            )
            mis_report_instance.unlink()

    def _mis_budget_item(self, budget_kpi_id, date_range, kpi_id, amount):
        kpi_expression_id = self.env['mis.report.kpi.expression'].search([('kpi_id', "=", kpi_id.id)], limit=1)
        date_from = date_range.date_start if not self.use_last_year else date_range.date_start - relativedelta(years=1)
        date_to = date_range.date_end if not self.use_last_year else date_range.date_end - relativedelta(years=1)
        self.env['mis.budget.item'].create({
            'budget_id': budget_kpi_id.id,
            'report_id': budget_kpi_id.report_id,
            'date_from': date_range.date_start,
            'date_to':  date_range.date_end,
            'kpi_expression_id': kpi_expression_id.id,
            'amount': amount
        })

    def _get_date_(self, date_range):
        date_from = date_range.date_start if not self.use_last_year else date_range.date_start - relativedelta(years=1)
        date_to = date_range.date_end if not self.use_last_year else date_range.date_end - relativedelta(years=1)
        return date_from, date_to
