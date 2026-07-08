"""Company Chart Variant — template + custom accounts."""

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountChartVariant(models.Model):
    _name = "account.chart.variant"
    _description = "Account Chart Variant"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    template_id = fields.Many2one(
        "account.chart.template",
        string="Base Template",
        help="BAS template this variant is based on",
    )
    custom_account_ids = fields.One2many(
        "account.chart.variant.line",
        "variant_id",
        string="Custom Accounts",
        help="Accounts added or modified by the company",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("name_company_uniq", "UNIQUE(name, company_id)",
         "Chart variant name must be unique per company!"),
    ]


class AccountChartVariantLine(models.Model):
    _name = "account.chart.variant.line"
    _description = "Account Chart Variant Line"
    _order = "code"

    variant_id = fields.Many2one(
        "account.chart.variant",
        string="Variant",
        required=True,
        ondelete="cascade",
    )
    code = fields.Char(string="Account Code", required=True)
    name = fields.Char(string="Account Name", required=True)
    action = fields.Selection([
        ("add", "Add"),
        ("modify", "Modify"),
        ("remove", "Remove"),
    ], string="Action", required=True, default="add")
    account_type = fields.Char(string="Account Type")
    notes = fields.Text(string="Notes")


class AccountChartSnapshot(models.Model):
    _name = "account.chart.snapshot"
    _description = "Account Chart Snapshot"
    _order = "fiscalyear_id, code"

    fiscalyear_id = fields.Many2one(
        "account.fiscal.year",
        string="Fiscal Year",
        required=True,
        ondelete="cascade",
        index=True,
    )
    variant_id = fields.Many2one(
        "account.chart.variant",
        string="Chart Variant",
        help="The variant used for this fiscal year",
    )
    account_id = fields.Many2one(
        "account.account",
        string="Account",
        required=True,
        ondelete="cascade",
    )
    code = fields.Char(related="account_id.code", string="Code", store=True)
    name = fields.Char(related="account_id.name", string="Name", store=True)
    account_type = fields.Char(related="account_id.account_type", string="Type", store=True)
    company_id = fields.Many2one(
        related="fiscalyear_id.company_id",
        store=True,
    )
