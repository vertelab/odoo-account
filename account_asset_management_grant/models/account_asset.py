from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    account_asset_grant_ids = fields.One2many(
        'account.asset.grant',
        'account_asset_id',
        string="Grants"
    )
    grant_move_ids = fields.One2many(
        'account.move',
        compute='_compute_grant_moves',
        string="Grant Moves"
    )
    grant_count = fields.Integer(
        string="Grants",
        compute='_compute_grant_count'
    )
    grant_move_count = fields.Integer(
        string="Grant Entries",
        compute='_compute_grant_moves'
    )

    total_grant_amount = fields.Monetary(
        string="Total Grants",
        compute='_compute_total_grant_amount',
        store=True,
    )

    @api.depends('account_asset_grant_ids')
    def _compute_grant_count(self):
        for asset in self:
            asset.grant_count = len(asset.account_asset_grant_ids)

    @api.depends('account_asset_grant_ids.move_id')
    def _compute_grant_moves(self):
        for asset in self:
            moves = asset.account_asset_grant_ids.mapped('move_id')
            asset.grant_move_ids = moves
            asset.grant_move_count = len(moves)

    @api.depends('account_asset_grant_ids.amount', 'account_asset_grant_ids.move_id')
    def _compute_total_grant_amount(self):
        """Calculate total amount of posted grants"""
        for asset in self:
            posted_grants = asset.account_asset_grant_ids.filtered('move_id')
            asset.total_grant_amount = sum(posted_grants.mapped('amount'))

    @api.depends("purchase_value", "salvage_value", "method", "total_grant_amount")
    def _compute_depreciation_base(self):
        """Override to subtract grants from depreciation base"""
        for asset in self:
            if asset.method in ["linear-limit", "degr-limit"]:
                asset.depreciation_base = asset.purchase_value - asset.total_grant_amount
            else:
                depreciable_amount = asset.purchase_value - asset.salvage_value
                asset.depreciation_base = depreciable_amount - asset.total_grant_amount

    def compute_depreciation_board(self):
        """
        Override to ensure create line is updated with grants before computation.
        This ensures the depreciation base matches the create line amount.
        """
        # Update create line for all assets BEFORE calling parent method
        for asset in self:
            create_line = asset.depreciation_line_ids.filtered(lambda l: l.type == 'create')
            if create_line and create_line.amount != asset.depreciation_base:
                create_line.with_context(allow_asset_line_update=True).write({
                    'amount': asset.depreciation_base,
                })

        # Call the parent method which does all the complex calculation
        return super().compute_depreciation_board()

    def action_view_grants(self):
        """Smart button action to view grants"""
        self.ensure_one()
        return {
            'name': _('Asset Grants'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.asset.grant',
            'view_mode': 'list,form',
            'domain': [('account_asset_id', '=', self.id)],
            'context': {'default_account_asset_id': self.id}
        }

    def action_view_grant_moves(self):
        """Smart button action to view grant journal entries"""
        self.ensure_one()
        return {
            'name': _('Grant Journal Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.grant_move_ids.ids)],
        }