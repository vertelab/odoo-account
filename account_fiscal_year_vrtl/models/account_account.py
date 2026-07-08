"""Account Account integration — period-based balance methods."""

from odoo import models


class AccountAccount(models.Model):
    _inherit = "account.account"

    def get_debit_credit_balance(self, period, target_move="posted"):
        """Get debit/credit/balance for account within a period.

        Args:
            period: account.period record
            target_move: 'posted', 'draft', or 'all'

        Returns:
            dict with debit, credit, balance keys
        """
        self.ensure_one()
        if not period:
            return {"debit": 0.0, "credit": 0.0, "balance": 0.0}

        domain = [
            ("account_id", "=", self.id),
            ("date", ">=", period.date_start),
            ("date", "<=", period.date_stop),
            ("company_id", "=", period.company_id.id),
        ]
        if target_move == "posted":
            domain.append(("move_id.state", "=", "posted"))
        elif target_move != "all":
            domain.append(("move_id.state", "!=", "cancel"))

        result = self.env["account.move.line"].read_group(
            domain, ["debit", "credit"], []
        )
        if result:
            debit = result[0].get("debit", 0.0)
            credit = result[0].get("credit", 0.0)
            return {
                "debit": debit,
                "credit": credit,
                "balance": debit - credit,
            }
        return {"debit": 0.0, "credit": 0.0, "balance": 0.0}

    def get_balance(self, period, target_move="posted"):
        """Get balance for account within a period."""
        result = self.get_debit_credit_balance(period, target_move)
        return result["balance"]

    def sum_period(self):
        """Sum of balances across a period range (uses context period_start/period_stop)."""
        period_start = self.env.context.get("period_start")
        period_stop = self.env.context.get("period_stop")
        target_move = self.env.context.get("target_move", "posted")

        if not period_start or not period_stop:
            return {}

        periods = self.env["account.period"].get_period_ids(
            self.env["account.period"].browse(period_start),
            self.env["account.period"].browse(period_stop),
        )
        result = {}
        for account in self:
            total = 0.0
            for period_id in periods:
                period = self.env["account.period"].browse(period_id)
                total += account.get_balance(period, target_move)
            result[account.id] = total
        return result
