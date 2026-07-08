"""MIS Report Instance Period — 'account_balance' source."""

from odoo import api, fields, models


class MisReportInstancePeriod(models.Model):
    _inherit = "mis.report.instance.period"

    @api.depends("source")
    def _compute_source_aml_model_id(self):
        """Set source_aml_model_id to account.balance for 'account_balance' source."""
        res = super()._compute_source_aml_model_id()
        for period in self:
            if period.source == "account_balance":
                period.source_aml_model_id = self.env["ir.model"].search([
                    ("model", "=", "account.balance"),
                ], limit=1).id
        return res

    def _get_additional_move_line_filter(self):
        """Add fiscalyear_id filter for account_balance source."""
        domain = super()._get_additional_move_line_filter()
        if self.source == "account_balance":
            # The fiscalyear context is set from the MIS report instance
            fy_id = self.env.context.get("fiscalyear_id")
            if fy_id:
                domain.append(("fiscalyear_id", "=", fy_id))
        return domain
