from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

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

    def action_aggregate_account_analytic(self):
        active_ids = self.env.context.get('active_ids')
        analytic_budget_ids = self.env['mis.budget.by.analytic.account'].browse(active_ids)

        date_from = all(self._check_same_date(analytic_budget_ids.mapped('date_from')))
        date_to = all(self._check_same_date(analytic_budget_ids.mapped('date_to')))

        if not date_from and not date_to:
            raise ValidationError("Analytic Accounts are not in the same date range")

        budget_id = self.env['mis.budget.by.analytic.account'].create({
            'name': 'New Budget',
            'date_range_id': analytic_budget_ids[0].date_range_id.id,
            'date_from': analytic_budget_ids[0].date_from,
            'date_to': analytic_budget_ids[0].date_to,
        })

        if budget_id:

            body = _('%s was aggregated from:', budget_id.name)
            body += '<ul>'

            for analytic_budget_id in analytic_budget_ids:
                for analytic_item in analytic_budget_id.item_ids:
                    item_id = self.env['mis.budget.by.analytic.account.item'].search([
                        ('date_from', '=', analytic_item.date_from),
                        ('date_to', '=', analytic_item.date_to),
                        ('analytic_account_id', '=', analytic_item.analytic_account_id.id),
                        ('budget_id', '=', budget_id.id)
                    ])
                    if not item_id:
                        item_id = analytic_item.copy({'budget_id': budget_id.id})
                    else:
                        item_id.write({
                            'balance': item_id.balance + analytic_item.balance,
                        })

                body += "<li class='text-info'>%s</li>" % analytic_budget_id.name

            body += '</ul>'
            budget_id.message_post(body=body)

    def _check_same_date(self, date_time_list):
        valid = []
        for count in range(len(date_time_list)):
            for date_time in date_time_list:
                if date_time == date_time_list[count]:
                    valid.append(True)
                else:
                    valid.append(False)
            break
        return valid


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
