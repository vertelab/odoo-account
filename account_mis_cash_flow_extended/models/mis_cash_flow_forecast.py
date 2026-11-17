from odoo import fields, models


class MisCashFlowForecast(models.Model):

    _name = "mis.cash.flow.forecast"
    _description = "MIS Cash Flow Forecast"
    _inherit = ["mis.budget.abstract", "mail.thread"]

    # item_ids = fields.One2many(
    #     comodel_name="mis.cash.flow.forecast_line", inverse_name="forecast_id", copy=True
    # )
    item_ids = fields.Many2one(
        comodel_name="mis.cash.flow.forecast_line"
    )
    company_id = fields.Many2one(required=True)
    allow_items_overlap = fields.Boolean(
        help="If checked, overlap between budget items is allowed"
    )