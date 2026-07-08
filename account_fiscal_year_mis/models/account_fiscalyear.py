"""Fiscal Year extension — balance records and OCA closing integration."""

import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class AccountFiscalYear(models.Model):
    _inherit = "account.fiscal.year"

    outgoing_balance_record_ids = fields.One2many(
        "account.balance",
        "fiscalyear_id",
        string="Outgoing Balances",
    )
    outgoing_balance_count = fields.Integer(
        string="Balance Records",
        compute="_compute_outgoing_balance_count",
    )

    def _compute_outgoing_balance_count(self):
        for fy in self:
            fy.outgoing_balance_count = len(fy.outgoing_balance_record_ids)

    def create_balance(self):
        """Create balance records via OCA account_fiscal_year_closing.

        Delegates to the OCA closing wizard for proper account mapping
        and closing type handling (balance/unreconciled).
        """
        self.ensure_one()
        # Use OCA closing for proper balance creation
        closing = self.env["account.fiscalyear.closing"].create({
            "name": _("Balance %s", self.name),
            "year": self.date_to.year,
            "date_start": self.date_from,
            "date_end": self.date_to,
            "date_opening": fields.Date.add(self.date_to, days=1),
            "company_id": self.company_id.id,
        })
        closing.button_calculate()
        closing.button_post()

        # After OCA closing, populate our account.balance records
        self._populate_balance_from_closing(closing)
        _logger.info("Created balance for fiscal year '%s'", self.name)
        return True

    def _populate_balance_from_closing(self, closing):
        """Create account.balance records from OCA closing moves."""
        self.ensure_one()
        # Remove old balances
        self.outgoing_balance_record_ids.unlink()

        # Read closing move lines to create balance records
        for move in closing.move_ids:
            for line in move.line_ids:
                self.env["account.balance"].create({
                    "fiscalyear_id": self.id,
                    "account_id": line.account_id.id,
                    "debit": line.debit,
                    "credit": line.credit,
                    "date": move.date,
                    "company_id": self.company_id.id,
                    "currency_id": line.currency_id.id or self.company_id.currency_id.id,
                })

    def open_balances(self):
        """Open window action displaying balance records."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Balances: %s", self.name),
            "res_model": "account.balance",
            "view_mode": "tree,form",
            "domain": [("fiscalyear_id", "=", self.id)],
            "target": "current",
        }
