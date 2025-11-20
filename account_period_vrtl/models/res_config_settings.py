from odoo import models, fields, api
from datetime import datetime, timedelta


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    period_closing_date = fields.Date(
        string='Account Period Closing Date',
        related='company_id.period_closing_date',
        readonly=False,
        help="Account Period Closing Date",
    )