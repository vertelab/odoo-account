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
        """Search moves by period — translates to date range search."""
        if not value:
            return []
        if isinstance(value, bool):
            return []
        if operator in ("=", "in", "!=", "not in"):
            if isinstance(value, (int, str)):
                value = [int(value)]
            periods = self.env["account.period"].browse(value)
            if not periods:
                return [("id", "=", False)]
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
            else:
                if len(date_domains) == 1:
                    dom = date_domains[0]
                    return ["!", dom[0], dom[1], dom[2]]
                return ["!"] + [
                    dom for pair in date_domains for dom in pair
                ]
        return [("id", "=", False)]

    def _is_bypassing_period_lock(self):
        """Check if this move's journal bypasses period locks."""
        self.ensure_one()
        return self.journal_id.bypass_period_lock

    def _has_period_exception(self, period):
        """Check if this move has a valid period exception.

        Considers both journal bypass and user exceptions.
        """
        self.ensure_one()
        if not period or period.state != "done":
            return False

        # Hash-locked periods: only journal bypass works, no user exceptions
        if period.company_id.close_period_hash_lock:
            return self.journal_id.bypass_period_lock

        # Soft-closed period: check journal bypass first, then user exceptions
        if self.journal_id.bypass_period_lock:
            return True

        exception = self.env["account.period.exception"]._get_user_period_exception(
            period
        )
        if exception:
            _logger.info(
                "Period exception granted for period '%s' to user '%s': %s",
                period.name, self.env.user.name, exception.reason,
            )
            return True

        return False

    @api.model_create_multi
    def create(self, vals_list):
        """Validate moves are not created in closed periods."""
        for vals in vals_list:
            if vals.get("date"):
                period = self.env["account.period"].date2period(vals["date"])
                if period and period.state == "done":
                    # Check journal + period exception (dummy check on vals)
                    if vals.get("journal_id"):
                        journal = self.env["account.journal"].browse(vals["journal_id"])
                        if journal.bypass_period_lock:
                            _logger.info(
                                "Bypassing closed period '%s' for journal '%s'",
                                period.name, journal.name,
                            )
                            continue
                    # Check user exception
                    exception = self.env["account.period.exception"]._get_user_period_exception(
                        period
                    )
                    if exception:
                        _logger.info(
                            "Period exception for '%s': user '%s' — %s",
                            period.name, self.env.user.name, exception.reason,
                        )
                        continue
                    raise UserError(
                        _("Cannot create move with date %(date)s: period '%(period)s' is closed. "
                          "Use a closing journal or request a period exception.",
                          date=vals["date"], period=period.name)
                    )
        return super().create(vals_list)

    def write(self, vals):
        """Validate moves are not modified in closed periods."""
        if vals.get("date"):
            for move in self:
                period = self.env["account.period"].date2period(vals["date"])
                if period and period.state == "done":
                    if move._has_period_exception(period):
                        continue
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
                    if move._has_period_exception(period):
                        continue
                    raise UserError(
                        _("Cannot post move '%(move)s' with date %(date)s: period '%(period)s' is closed. "
                          "Use a closing journal or request a period exception.",
                          move=move.name, date=move.date, period=period.name)
                    )
        return super().action_post()

    def _reverse_moves(self, default_values_list=None, cancel=False):
        """Set date on reversal moves."""
        return super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)

    @api.onchange("date", "invoice_date")
    def _onchange_date_period(self):
        """Check if the selected date falls in a closed period (UI warning)."""
        if self.date:
            period = self.env["account.period"].date2period(self.date)
            if period and period.state == "done":
                if self._has_period_exception(period):
                    return {}
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
