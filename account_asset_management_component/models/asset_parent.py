from odoo import models, fields, api, _


class Project(models.Model):
    _name = "asset.parent"
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _description = "Asset Parent"
    _order = "code, name"
    _check_company_auto = True

    name = fields.Char(string="Name", required=True, )

    code = fields.Char(
        string="Reference",
        size=32,
    )
    purchase_value = fields.Monetary(
        compute="_compute_value",
        required=True,
        help="This amount represent the initial value of the asset."
             "\nThe Depreciation Base is calculated as follows:"
             "\nPurchase Value - Salvage Value.",
    )
    salvage_value = fields.Monetary(
        compute="_compute_value",
        readonly=False,
        help="The estimated value that an asset will realize upon "
             "its sale at the end of its useful life.\n"
             "This value is used to determine the depreciation amounts.",
    )
    depreciation_base = fields.Monetary(
        compute="_compute_value",
        help="This amount represent the depreciation base "
             "of the asset (Purchase Value - Salvage Value).",
    )
    value_residual = fields.Monetary(
        compute="_compute_value",
        string="Residual Value",
    )
    value_depreciated = fields.Monetary(
        compute="_compute_value",
        string="Depreciated Value",
    )

    @api.depends('account_asset_ids')
    def _compute_value(self):
        for rec in self:
            rec.salvage_value = sum(rec.account_asset_ids.mapped('salvage_value'))
            rec.purchase_value = sum(rec.account_asset_ids.mapped('purchase_value'))
            rec.depreciation_base = sum(rec.account_asset_ids.mapped('depreciation_base'))
            rec.value_residual = sum(rec.account_asset_ids.mapped('value_residual'))
            rec.value_depreciated = sum(rec.account_asset_ids.mapped('value_depreciated'))

    @api.model
    def _default_company_id(self):
        return self.env.company

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self._default_company_id(),
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Company Currency",
        store=True,
    )

    active = fields.Boolean(default=True)

    account_asset_ids = fields.One2many('account.asset', 'asset_parent_id', string="Assets")

    def action_view_account_assets(self):
        return {
            'name': _('Assets'),
            'view_mode': 'tree,form',
            'res_model': 'account.asset',
            'type': 'ir.actions.act_window',
            'domain': [('asset_parent_id', '=', self.id)],
            'context': {
                'default_asset_parent_id': self.id
            },
        }
