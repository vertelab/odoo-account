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

    def compute_fiscalyear_dates(self, current_date):
        """Get fiscal year dates for a given date.

        Centralized lookup — searches manual fiscal year records first,
        falls back to calendar year computation.

        Args:
            current_date: Date to find fiscal year for

        Returns:
            dict with date_from, date_to keys (and optional record)
        """
        self.ensure_one()
        fy = self.env["account.fiscal.year"].search([
            ("company_id", "=", self.id),
            ("date_from", "<=", str(current_date)),
            ("date_to", ">=", str(current_date)),
        ], limit=1)
        if fy:
            return {
                "date_from": fy.date_from,
                "date_to": fy.date_to,
                "record": fy,
            }

        # Fallback to calendar year
        from odoo.tools.date_utils import get_fiscal_year
        last_day = self.fiscalyear_last_day if hasattr(self, "fiscalyear_last_day") else 31
        last_month = int(self.fiscalyear_last_month) if hasattr(self, "fiscalyear_last_month") else 12
        date_from, date_to = get_fiscal_year(current_date, day=last_day, month=last_month)
        return {"date_from": date_from, "date_to": date_to}
