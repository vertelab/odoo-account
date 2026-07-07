# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools import SQL


class MisBudgetForecastReport(models.Model):
    _name = "mis.budget.forecast.report"
    _description = "MIS Budget Forecast Report"
    _auto = False
    _order = "budget_id, account_code, date_from"

    budget_id = fields.Many2one(
        "mis.budget.by.account", string="Budget", readonly=True
    )
    item_id = fields.Many2one(
        "mis.budget.by.account.item", string="Budget Item", readonly=True
    )
    name = fields.Char(string="Description", readonly=True)
    account_id = fields.Many2one(
        "account.account", string="Account", readonly=True
    )
    account_code = fields.Char(string="Account Code", readonly=True)
    date_from = fields.Date(string="From", readonly=True)
    date_to = fields.Date(string="To", readonly=True)
    budget_amount = fields.Float(string="Budget", readonly=True)
    actual_amount = fields.Float(string="Actual", readonly=True)
    forecast_amount = fields.Float(string="Forecast", readonly=True)
    deviation = fields.Float(string="Deviation", readonly=True)
    is_forecast = fields.Boolean(string="Is Forecast", readonly=True)
    is_passed = fields.Boolean(string="Period Passed", readonly=True)
    company_id = fields.Many2one(
        "res.company", string="Company", readonly=True
    )

    @property
    def _table_query(self):
        """
        SQL view som beräknar prognos per budget-item.

        Inspirerad av EE:s budget.report men enklare —
        vi unionar inte, utan läser direkt från mis.budget.by.account.item
        som redan har actual_amount computed.
        """
        self.env["mis.budget.by.account.item"].flush_model()
        self.env["account.account"].flush_model()
        self.env["mis.budget.by.account"].flush_model()

        return SQL(
            """
            SELECT
                item.id AS id,
                item.budget_id AS budget_id,
                item.id AS item_id,
                item.name AS name,
                item.account_id AS account_id,
                aa.code AS account_code,
                item.date_from AS date_from,
                item.date_to AS date_to,
                item.balance AS budget_amount,
                item.actual_amount AS actual_amount,
                CASE
                    WHEN budget.is_forecast
                         AND item.date_to IS NOT NULL
                         AND item.date_to < COALESCE(budget.forecast_cutoff_date, CURRENT_DATE)
                    THEN item.actual_amount
                    ELSE item.balance
                END AS forecast_amount,
                CASE
                    WHEN budget.is_forecast
                         AND item.date_to IS NOT NULL
                         AND item.date_to < COALESCE(budget.forecast_cutoff_date, CURRENT_DATE)
                    THEN item.actual_amount - item.balance
                    ELSE 0.0
                END AS deviation,
                COALESCE(budget.is_forecast, FALSE) AS is_forecast,
                CASE
                    WHEN item.date_to IS NOT NULL
                         AND item.date_to < COALESCE(budget.forecast_cutoff_date, CURRENT_DATE)
                    THEN TRUE
                    ELSE FALSE
                END AS is_passed,
                item.company_id AS company_id
            FROM mis_budget_by_account_item item
            JOIN mis_budget_by_account budget ON budget.id = item.budget_id
            LEFT JOIN account_account aa ON aa.id = item.account_id
            WHERE budget.active = TRUE
            """
        )

    def action_open_budget_item(self):
        """Open the source budget item."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "mis.budget.by.account.item",
            "view_mode": "form",
            "res_id": self.item_id.id,
        }
