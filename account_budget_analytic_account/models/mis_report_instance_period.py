from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MisReportInstancePeriod(models.Model):
    _inherit = 'mis.report.instance.period'


    source = fields.Selection(
        selection_add=[
            ("mis_budget_by_analytic_account", "MIS Budget by analytic account"),
        ],
        ondelete={
            "mis_budget_by_analytic_account": "cascade",
        },
    )

    source_mis_budget_by_analytic_account_id = fields.Many2one(
        comodel_name="mis.budget.by.analytic.account", string="Budget by Analytic Account"
    )

    @api.constrains("source_aml_model_id")
    def _check_source_aml_model_id_depricated(self):
        for record in self:
            if record.source_aml_model_id:
                if record.source_aml_model_id.model == 'mis.budget.by.analytic.account.item':
                    record_model = (
                        record.source_aml_model_id.sudo()
                        .field_id.filtered(lambda r: r.name == "analytic_account_id")
                        .relation
                    )
                else:
                    record_model = (
                        record.source_aml_model_id.sudo()
                        .field_id.filtered(lambda r: r.name == "account_id")
                        .relation
                    )
                report_account_model = record.report_id.account_model
                if record_model != report_account_model:
                    raise ValidationError(
                        _(
                            "Actual (alternative) models used in columns must "
                            "have the same account model in the Account field and must "
                            "be the same defined in the "
                            "report template: %s"
                        )
                        % report_account_model
                    )
