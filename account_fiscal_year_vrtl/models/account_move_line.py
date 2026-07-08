"""Account Move Line integration — no period_id or fiscalyear_id fields."""

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # NO period_id — removed. Period is derived from move.date
    # NO fiscalyear_id — removed.
    # NO latest_payment_date — removed.
