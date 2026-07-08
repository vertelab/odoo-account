"""Chart Diff Wizard — shows changes when switching fiscal year charts."""

from odoo import _, fields, models


class AccountChartDiffWizard(models.TransientModel):
    _name = "account.chart.diff.wizard"
    _description = "Chart of Accounts Diff Wizard"

    fiscalyear_id = fields.Many2one(
        "account.fiscal.year",
        string="Target Fiscal Year",
        required=True,
    )
    change_line_ids = fields.One2many(
        "account.chart.diff.line",
        "wizard_id",
        string="Changes",
        readonly=True,
    )

    def action_compute_diff(self):
        """Compute chart differences for the selected fiscal year."""
        self.ensure_one()
        changes = self.fiscalyear_id._compute_chart_diff()
        self.change_line_ids.unlink()
        for change in changes:
            self.env["account.chart.diff.line"].create({
                "wizard_id": self.id,
                "action": change["action"],
                "code": change["code"],
                "name": change.get("name", ""),
                "account_type": change.get("account_type", ""),
            })
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.chart.diff.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_apply(self):
        """Apply the chart variant to the fiscal year."""
        self.ensure_one()
        self.fiscalyear_id.action_apply_chart_variant()
        return {"type": "ir.actions.act_window_close"}


class AccountChartDiffLine(models.TransientModel):
    _name = "account.chart.diff.line"
    _description = "Chart Diff Line"

    wizard_id = fields.Many2one(
        "account.chart.diff.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    action = fields.Selection([
        ("add", "Add"),
        ("modify", "Modify"),
        ("remove", "Remove"),
    ], string="Action", readonly=True)
    code = fields.Char(string="Code", readonly=True)
    name = fields.Char(string="Name", readonly=True)
    account_type = fields.Char(string="Type", readonly=True)
