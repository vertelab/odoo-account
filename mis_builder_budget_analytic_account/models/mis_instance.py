from odoo import api, fields, models


class MisReportInstancePeriod(models.Model):
    _inherit = 'mis.report.instance.period'

    source_mis_budget_by_analytic_account_id = fields.Many2one(
        comodel_name="mis.budget.by.analytic.account", string="Budget by Analytic Account"
    )