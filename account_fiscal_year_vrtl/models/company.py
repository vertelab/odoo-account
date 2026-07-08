"""Company settings for fiscal year and periods."""

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    period_closing_date = fields.Date(
        string="Default Period Closing Date",
        help="Default date when periods should be automatically closed. "
             "Can be overridden per period.",
    )
    close_period_hash_lock = fields.Boolean(
        string="Hash-Lock on Period Close",
        default=False,
        help="When enabled, all posted moves in a period will be hash-locked "
             "(inalterable) when the period is closed. "
             "WARNING: This is destructive — hash-locked moves cannot be modified "
             "even by administrators.",
    )

    def setting_init_fiscal_year_action(self):
        """Return window action for fiscal year creation form."""
        return {
            "type": "ir.actions.act_window",
            "name": "Create Fiscal Year",
            "res_model": "account.fiscal.year",
            "view_mode": "form",
            "target": "new",
        }

    # compute_fiscalyear_dates() is inherited from OCA account_fiscal_year
    # No need to redefine — the OCA version already handles:
    # 1. Search manual fiscal year records first
    # 2. Fallback to fiscalyear_last_day/fiscalyear_last_month
    # 3. Handle gaps between records
