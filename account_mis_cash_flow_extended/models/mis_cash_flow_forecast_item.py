from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class MisCashFlowForecastLine(models.Model):

    _inherit = "mis.cash_flow.forecast_line"

    forecast_factor = fields.Float(string="Forecast Factor")
    adjusted_balance = fields.Float(string="Adjusted Balance")
    summed_budget_balance = fields.Float(string="Budget Balance Sum")
    summed_result_balance = fields.Float(string="Result Balance Sum")
    budget_balance_average = fields.Float(string="Average Budget Balance")
    result_balance_average = fields.Float(string="Average Result Balance")