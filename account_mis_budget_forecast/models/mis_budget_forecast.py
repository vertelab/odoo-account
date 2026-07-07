# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date


class MisBudgetByAccount(models.Model):
    _inherit = "mis.budget.by.account"

    is_forecast = fields.Boolean(
        string="Is Forecast",
        default=False,
        tracking=True,
        help="When enabled, this budget becomes a dynamic forecast. "
             "Passed periods show actual booked amounts instead of budget figures. "
             "Future periods continue to show the planned budget.",
    )
    forecast_cutoff_date = fields.Date(
        string="Forecast Cutoff Date",
        default=lambda self: date.today(),
        help="Periods ending before this date will show actual results. "
             "Periods starting on or after this date will show budget figures. "
             "Defaults to today.",
    )

    def action_set_as_forecast(self):
        """Convert this budget into a dynamic forecast."""
        self.ensure_one()
        self.write({
            'is_forecast': True,
            'forecast_cutoff_date': date.today(),
        })

    def action_unset_forecast(self):
        """Revert forecast back to a static budget."""
        self.ensure_one()
        self.write({
            'is_forecast': False,
        })

    def action_compute_forecast_items(self):
        """Trigger recomputation of forecast_amount on all budget items."""
        self.ensure_one()
        self.item_ids._compute_forecast_amount()
