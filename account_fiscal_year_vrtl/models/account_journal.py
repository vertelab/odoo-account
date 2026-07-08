"""Account Journal extension — bypass period lock flag."""

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    bypass_period_lock = fields.Boolean(
        string="Allow in Closed Periods",
        default=False,
        help="When enabled, moves in this journal can be posted in closed periods. "
             "Intended for year-end closing journals where adjustments may be needed "
             "months after the period has been closed.",
    )
