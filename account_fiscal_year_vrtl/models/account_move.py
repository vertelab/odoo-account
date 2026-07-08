"""Account Move integration — period validation without stored period_id."""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    # NO period_id field — period is derived from date via date2period()

    def _get_period(self):
        """Get the period for this move's date. Display-only helper."""
        self.ensure_one()
        if self.date:
            return self.env["account.period"].date2period(self.date)
        return self.env["account.period"].browse()

    def _search_period_id(self, operator, value):
        """Search moves by period — translates to date range search.

        Since we don't have a stored period_id, we convert period search
        to date range conditions.
        """
        if not value:
            return []

        if isinstance(value, bool):
            return []

        # Get period(s) by ID
        if operator in ("=", "in", "!=", "not in"):
            if isinstance(value, (int, str)):
                value = [int(value)]
            periods = self.env["account.period"].browse(value)
            if not periods:
                return [("id", "=", False)]  # No matching periods → no results

            # Build date range domains
            date_domains = []
            for period in periods:
                date_domains.append([
                    ("date", ">=", period.date_start),
                    ("date", "<=", period.date_stop),
                ])

            if operator in ("=", "in"):
                if len(date_domains) == 1:
                    return date_domains[0]
                return ["|"] * (len(date_domains) - 1) + [
                    dom for pair in date_domains for dom in pair
                ]
            else:  # !=, not in
                if len(date_domains) == 1:
                    dom = date_domains[0]
                    return ["!", dom[0], dom[1], dom[2]]
                return ["!"] + [
                    dom for pair in date_domains for dom in pair
                ]

        return [("id", "=", False)]  # Unsupported operator → no results

    @api.model_create_multi
    def create(self, vals_list):
        """Validate moves are not created in closed periods."""
        # First, resolve dates
        for vals in vals_list:
            if vals.get("date"):
                period = self.env["account.period"].date2period(vals["date"])
                if period and period.state == "done":
                    raise UserError(
                        _("Cannot create move with date %(date)s: period '%(period)s' is closed.",
                          date=vals["date"], period=period.name)
                    )
        return super().create(vals_list)

    def write(self, vals):
        """Validate moves are not modified in closed periods."""
        if vals.get("date"):
            for move in self:
                period = self.env["account.period"].date2period(vals["date"])
                if period and period.state == "done":
                    raise UserError(
                        _("Cannot set date %(date)s on move '%(move)s': period '%(period)s' is closed.",
                          date=vals["date"], move=move.name, period=period.name)
                    )
        return super().write(vals)

    def action_post(self):
        """Validate moves are not posted in closed periods."""
        for move in self:
            if move.date:
                period = self.env["account.period"].date2period(move.date)
                if period and period.state == "done":
                    raise UserError(
                        _("Cannot post move '%(move)s' with date %(date)s: period '%(period)s' is closed.",
                          move=move.name, date=move.date, period=period.name)
                    )
        return super().action_post()

    def _reverse_moves(self, default_values_list=None, cancel=False):
        """Set date on reversal moves."""
        res = super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)
        # Reversal moves get the reversal date, which should be in an open period
        return res

    @api.onchange("date", "invoice_date")
    def _onchange_date_period(self):
        """Check if the selected date falls in a closed period (UI warning)."""
        if self.date:
            period = self.env["account.period"].date2period(self.date)
            if period and period.state == "done":
                return {
                    "warning": {
                        "title": _("Closed Period"),
                        "message": _(
                            "The date %(date)s falls in period '%(period)s' which is closed.",
                            date=self.date, period=period.name,
                        ),
                    }
                }
        return {}
