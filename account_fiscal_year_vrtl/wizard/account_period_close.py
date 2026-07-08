"""Period Close Wizard — with optional hash-locking."""

import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountPeriodClose(models.TransientModel):
    _name = "account.period.close"
    _description = "Close Period"

    sure = fields.Boolean(string="I understand the consequences", default=False)

    def data_save(self):
        """Close the selected period(s)."""
        active_ids = self.env.context.get("active_ids", [])
        if not active_ids:
            raise UserError(_("No periods selected."))

        periods = self.env["account.period"].browse(active_ids)

        for period in periods:
            if period.state == "done":
                continue

            # Check if fiscal year is already closed
            if period.fiscalyear_id and period.fiscalyear_id.state == "done":
                raise UserError(
                    _("Cannot close period '%(period)s': fiscal year '%(fy)s' is already closed.",
                      period=period.name, fy=period.fiscalyear_id.name)
                )

            # Hash-lock if enabled
            if self.env.company.close_period_hash_lock:
                _logger.info(
                    "Hash-locking moves in period '%s' (%s → %s)...",
                    period.name, period.date_start, period.date_stop,
                )
                # Find all posted moves in this period
                moves = self.env["account.move"].search([
                    ("date", ">=", period.date_start),
                    ("date", "<=", period.date_stop),
                    ("state", "=", "posted"),
                    ("company_id", "=", period.company_id.id),
                ])
                if moves:
                    try:
                        moves._hash_moves(force_hash=True)
                        _logger.info("Hash-locked %d moves in period '%s'", len(moves), period.name)
                    except Exception as e:
                        _logger.error("Failed to hash-lock moves: %s", e)
                        raise UserError(
                            _("Failed to hash-lock moves in period '%(period)s': %(error)s",
                              period=period.name, error=str(e))
                        )

            # Close the period
            period.state = "done"
            period.fiscalyear_id._set_state()
            _logger.info("Period '%s' closed", period.name)

        return {"type": "ir.actions.act_window_close"}


class CloseAccountPeriodJournal(models.TransientModel):
    _name = "close.account.period.journal"
    _description = "Close Period Journal"

    sure = fields.Boolean(string="I understand the consequences", default=False)

    def data_save(self):
        """Close the selected period journal entries."""
        # The period.journal records are passed via context
        active_ids = self.env.context.get("active_ids", [])
        if active_ids:
            journals = self.env["account.period.journal"].browse(active_ids)
            for journal in journals:
                journal.state = "done"
                journal.period_id.fiscalyear_id._set_state()

        return {"type": "ir.actions.act_window_close"}
