from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class Mis_Cash_Flow_Forecast_Line(models.Model):

    _inherit = "mis.cash_flow.forecast_line"

    forecast_factor = fields.Float(string="Forecast Factor")
    adjusted_balance = fields.Float(string="Adjusted Balance")