# Copyright 2026 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Auto-reconciliation wizard for batch reconciliation with two modes:
- Perfect Match: reconcile journal items with opposite balance
- Clear Account: clear accounts with zero balance
"""

from datetime import date

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError


class AccountAutoReconcileWizard(models.TransientModel):
    _name = "account.auto.reconcile.wizard"
    _description = "Account Automatic Reconciliation Wizard"
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    line_ids = fields.Many2many(
        comodel_name="account.move.line",
        string="Journal Items",
        help="Journal items from which we derive a preset for the wizard.",
    )
    from_date = fields.Date(string="From")
    to_date = fields.Date(
        string="To",
        default=fields.Date.context_today,
        required=True,
    )
    account_ids = fields.Many2many(
        comodel_name="account.account",
        string="Accounts",
        check_company=True,
        domain="[('reconcile', '=', True), ('account_type', '!=', 'off_balance')]",
    )
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Partners",
        check_company=True,
        domain="[('company_id', 'in', (False, company_id)), '|', "
        "('parent_id', '=', False), ('is_company', '=', True)]",
    )
    search_mode = fields.Selection(
        selection=[
            ("one_to_one", "Perfect Match"),
            ("zero_balance", "Clear Account"),
        ],
        string="Reconcile",
        required=True,
        default="one_to_one",
        help="Reconcile journal items with opposite balance or clear "
        "accounts with a zero balance.",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        domain = self.env.context.get("domain")
        if "line_ids" in fields_list and "line_ids" not in res and domain:
            amls = self.env["account.move.line"].search(domain)
            if amls:
                res.update(self._get_default_wizard_values(amls))
                res["line_ids"] = [Command.set(amls.ids)]
        return res

    @api.model
    def _get_default_wizard_values(self, amls):
        """Derive a preset configuration based on selected journal items."""
        return {
            "account_ids": (
                [Command.set(amls[0].account_id.ids)]
                if all(
                    aml.account_id == amls[0].account_id for aml in amls
                )
                else []
            ),
            "partner_ids": (
                [Command.set(amls[0].partner_id.ids)]
                if all(
                    aml.partner_id == amls[0].partner_id for aml in amls
                )
                else []
            ),
            "search_mode": (
                "zero_balance"
                if amls.company_currency_id.is_zero(
                    sum(amls.mapped("balance"))
                )
                else "one_to_one"
            ),
            "from_date": min(amls.mapped("date")),
            "to_date": max(amls.mapped("date")),
        }

    def _get_wizard_values(self):
        """Get the current wizard configuration as a dict."""
        self.ensure_one()
        return {
            "account_ids": (
                [Command.set(self.account_ids.ids)]
                if self.account_ids
                else []
            ),
            "partner_ids": (
                [Command.set(self.partner_ids.ids)]
                if self.partner_ids
                else []
            ),
            "search_mode": self.search_mode,
            "from_date": self.from_date,
            "to_date": self.to_date,
        }

    def _action_auto_reconcile(self):
        """Execute the auto-reconciliation based on the selected mode."""
        self.ensure_one()
        domain = self._get_reconcile_domain()
        amls = self.env["account.move.line"].search(domain)

        if not amls:
            raise UserError(
                _("No journal items found matching the criteria.")
            )

        if self.search_mode == "one_to_one":
            return self._reconcile_one_to_one(amls)
        elif self.search_mode == "zero_balance":
            return self._reconcile_zero_balance(amls)

    def _get_reconcile_domain(self):
        """Build the search domain for journal items to reconcile."""
        domain = [
            ("account_id.reconcile", "=", True),
            ("parent_state", "=", "posted"),
            ("reconciled", "=", False),
        ]
        if self.account_ids:
            domain.append(("account_id", "in", self.account_ids.ids))
        if self.partner_ids:
            domain.append(("partner_id", "in", self.partner_ids.ids))
        if self.from_date:
            domain.append(("date", ">=", self.from_date))
        if self.to_date:
            domain.append(("date", "<=", self.to_date))
        return domain

    def _reconcile_one_to_one(self, amls):
        """Reconcile journal items that have opposite balances and match exactly.
        Groups by (account, partner, currency) and matches debits against credits.
        """
        reconciled_count = 0
        # Group by account + partner + currency
        groups = {}
        for aml in amls:
            key = (aml.account_id.id, aml.partner_id.id, aml.currency_id.id)
            if key not in groups:
                groups[key] = self.env["account.move.line"]
            groups[key] |= aml

        for _key, group_amls in groups.items():
            debits = group_amls.filtered(lambda l: l.balance > 0)
            credits = group_amls.filtered(lambda l: l.balance < 0)

            # Match debits against credits by amount
            debit_by_amount = {}
            for debit in debits:
                amount = debit.amount_residual_currency or debit.amount_residual
                rounded = round(amount, 2)
                if rounded not in debit_by_amount:
                    debit_by_amount[rounded] = self.env["account.move.line"]
                debit_by_amount[rounded] |= debit

            for credit in credits:
                amount = credit.amount_residual_currency or credit.amount_residual
                rounded = round(-amount, 2)
                if rounded in debit_by_amount and debit_by_amount[rounded]:
                    debit = debit_by_amount[rounded][0]
                    (debit | credit).reconcile()
                    debit_by_amount[rounded] -= debit
                    reconciled_count += 1

        return {
            "type": "ir.actions.act_window_close",
            "infos": _(
                "%(count)s journal items have been reconciled.",
                count=reconciled_count,
            ),
        }

    def _reconcile_zero_balance(self, amls):
        """Reconcile all journal items within accounts that have zero balance.
        Groups by (account, partner) and checks if total balance is zero.
        """
        reconciled_count = 0
        groups = {}
        for aml in amls:
            key = (aml.account_id.id, aml.partner_id.id)
            if key not in groups:
                groups[key] = self.env["account.move.line"]
            groups[key] |= aml

        for _key, group_amls in groups.items():
            total_balance = sum(group_amls.mapped("balance"))
            if group_amls.company_currency_id.is_zero(total_balance):
                group_amls.reconcile()
                reconciled_count += len(group_amls)

        return {
            "type": "ir.actions.act_window_close",
            "infos": _(
                "%(count)s journal items have been reconciled.",
                count=reconciled_count,
            ),
        }

    def action_auto_reconcile(self):
        """Button action to run auto-reconciliation."""
        self.ensure_one()
        return self._action_auto_reconcile()
