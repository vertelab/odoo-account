"""Settings for fiscal year and period configuration."""

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    period_closing_date = fields.Date(
        related="company_id.period_closing_date",
        string="Default Period Closing Date",
        readonly=False,
        help="Default date when periods should be automatically closed.",
    )
    close_period_hash_lock = fields.Boolean(
        related="company_id.close_period_hash_lock",
        string="Hash-Lock on Period Close",
        readonly=False,
        help="When enabled, all posted moves in a period will be hash-locked "
             "when the period is closed.",
    )
