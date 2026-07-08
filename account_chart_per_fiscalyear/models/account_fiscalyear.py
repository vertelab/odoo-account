"""Fiscal Year extension — chart of accounts per fiscal year."""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountFiscalYear(models.Model):
    _inherit = "account.fiscal.year"

    chart_template_id = fields.Many2one(
        "account.chart.template",
        string="BAS Template",
        help="BAS chart of accounts version for this fiscal year",
    )
    chart_variant_id = fields.Many2one(
        "account.chart.variant",
        string="Chart Variant",
        help="Company chart variant used for this fiscal year",
    )
    chart_snapshot_ids = fields.One2many(
        "account.chart.snapshot",
        "fiscalyear_id",
        string="Chart Snapshot",
        help="Frozen copy of the chart of accounts for this fiscal year",
    )

    def action_freeze_chart(self):
        """Freeze the chart of accounts for this fiscal year.

        Creates a snapshot of all active accounts for audit trail.
        Should be called when the fiscal year is closed.
        """
        self.ensure_one()
        if not self.chart_snapshot_ids:
            accounts = self.env["account.account"].search([
                ("company_ids", "in", self.company_id.ids),
                ("deprecated", "=", False),
            ])
            for account in accounts:
                self.env["account.chart.snapshot"].create({
                    "fiscalyear_id": self.id,
                    "variant_id": self.chart_variant_id.id,
                    "account_id": account.id,
                })
            _logger.info(
                "Froze %d accounts for fiscal year '%s'",
                len(accounts), self.name,
            )

    def action_apply_chart_variant(self):
        """Apply chart variant changes to account.account.

        Creates, modifies, or deactivates accounts based on
        the selected chart variant (template + custom lines).
        """
        self.ensure_one()
        if not self.chart_variant_id:
            raise UserError(_("No chart variant selected for this fiscal year."))

        variant = self.chart_variant_id
        changes = self._compute_chart_diff()

        # Apply changes
        for change in changes:
            if change["action"] == "add":
                self._create_account_from_change(change)
            elif change["action"] == "modify":
                self._modify_account_from_change(change)
            elif change["action"] == "remove":
                self._deactivate_account_from_change(change)

        _logger.info(
            "Applied chart changes for fiscal year '%s': %d changes",
            self.name, len(changes),
        )

    def _compute_chart_diff(self):
        """Compute diff between current accounts and selected chart variant.

        Returns list of change dicts: {action, code, name, old_name, ...}
        """
        self.ensure_one()
        variant = self.chart_variant_id
        current_accounts = self.env["account.account"].search([
            ("company_ids", "in", self.company_id.ids),
            ("deprecated", "=", False),
        ])
        current_by_code = {a.code: a for a in current_accounts}

        changes = []

        # Template accounts
        if variant.template_id:
            for line in variant.template_id.account_line_ids:
                if line.code not in current_by_code and line.code:
                    changes.append({
                        "action": "add",
                        "code": line.code,
                        "name": line.name,
                        "account_type": line.account_type,
                        "sru_code": line.sru_code,
                    })

        # Custom variant changes
        for line in variant.custom_account_ids:
            if line.action == "add" and line.code not in current_by_code:
                changes.append({
                    "action": "add",
                    "code": line.code,
                    "name": line.name,
                    "account_type": line.account_type,
                })
            elif line.action == "modify" and line.code in current_by_code:
                changes.append({
                    "action": "modify",
                    "code": line.code,
                    "name": line.name,
                    "account_type": line.account_type,
                })
            elif line.action == "remove" and line.code in current_by_code:
                changes.append({
                    "action": "remove",
                    "code": line.code,
                })

        return changes

    def _create_account_from_change(self, change):
        """Create a new account.account from a chart change."""
        account_vals = {
            "code": change["code"],
            "name": change["name"],
            "account_type": change.get("account_type", "asset_current"),
            "company_ids": [(4, self.company_id.id)],
            "reconcile": change.get("account_type") in ("asset_receivable", "liability_payable"),
        }
        self.env["account.account"].create(account_vals)

    def _modify_account_from_change(self, change):
        """Modify an existing account from a chart change."""
        account = self.env["account.account"].search([
            ("code", "=", change["code"]),
            ("company_ids", "in", self.company_id.ids),
        ], limit=1)
        if account:
            vals = {}
            if change.get("name"):
                vals["name"] = change["name"]
            if vals:
                account.write(vals)

    def _deactivate_account_from_change(self, change):
        """Deactivate an account from a chart change."""
        account = self.env["account.account"].search([
            ("code", "=", change["code"]),
            ("company_ids", "in", self.company_id.ids),
        ], limit=1)
        if account:
            account.write({"deprecated": True})
