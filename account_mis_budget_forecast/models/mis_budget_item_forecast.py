# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import date


class MisBudgetByAccountItem(models.Model):
    _inherit = "mis.budget.by.account.item"

    forecast_amount = fields.Monetary(
        string="Forecast Amount",
        compute="_compute_forecast_amount",
        store=True,
        currency_field="company_currency_id",
        help="Dynamic forecast value: actual booked amount for past periods, "
             "budget amount for future periods. Only computed when parent budget "
             "has is_forecast=True.",
    )

    @api.depends(
        "budget_id.is_forecast",
        "budget_id.forecast_cutoff_date",
        "actual_amount",
        "balance",
        "date_to",
    )
    def _compute_forecast_amount(self):
        """
        Logik (inspirerad av Fortnox):
        - Om budgeten INTE är en prognos → forecast_amount = balance
        - Om budgeten ÄR en prognos:
          - perioden är helt passerad (date_to < cutoff_date) → actual_amount
          - perioden är framtida eller pågående → balance (budgetbelopp)
        """
        today = date.today()
        for rec in self:
            if not rec.budget_id.is_forecast:
                rec.forecast_amount = rec.balance
            else:
                cutoff = rec.budget_id.forecast_cutoff_date or today
                if rec.date_to and rec.date_to < cutoff:
                    # Period is fully in the past → use actuals
                    rec.forecast_amount = rec.actual_amount
                else:
                    # Period is current or future → use budget
                    rec.forecast_amount = rec.balance
