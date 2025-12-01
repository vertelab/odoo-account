from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountAssetGrant(models.Model):
    _name = 'account.asset.grant'
    _description = 'Account Asset Grant'

    name = fields.Char(string="Grant Name", required=True)
    amount = fields.Monetary(string="Amount", required=True)
    date = fields.Date(string="Date", required=True, default=fields.Date.today)
    account_asset_id = fields.Many2one(
        'account.asset',
        string="Account Asset",
        required=True,
        ondelete='cascade'
    )
    currency_id = fields.Many2one(
        related='account_asset_id.currency_id'
    )
    move_id = fields.Many2one(
        'account.move',
        string="Journal Entry",
        readonly=True
    )

    def action_create_grant(self):
        """Create journal entry for grant"""
        self.ensure_one()

        if self.move_id:
            raise UserError(_('Grant entry already created'))

        profile_id = self.account_asset_id.profile_id

        # Create journal entry
        move_vals = {
            'move_type': 'entry',
            'date': self.date,
            'ref': f"Grant: {self.name} - {self.account_asset_id.name}",
            'journal_id': profile_id.journal_id.id,
            'line_ids': [
                (0, 0, {
                    'name': f'{self.name} - Debit',
                    'account_id': profile_id.account_depreciation_id.id,
                    'debit': self.amount,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': f'{self.name} - Credit',
                    'account_id': profile_id.account_expense_depreciation_id.id,
                    'debit': 0.0,
                    'credit': self.amount,
                })
            ]
        }

        move = self.env['account.move'].with_context(
            check_move_validity=False
        ).create(move_vals)

        # Post the entry
        move.action_post()

        # Link the move to grant
        self.move_id = move.id

        # Recompute depreciation board - will now use our override
        if self.account_asset_id.state in ['open', 'close']:
            self.account_asset_id.compute_depreciation_board()

        # Close wizard and refresh
        return {'type': 'ir.actions.act_window_close'}

    def action_view_move(self):
        self.ensure_one()
        if not self.move_id:
            raise UserError(_('No journal entry found'))

        return {
            'name': _('Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
            'target': 'current',
        }

    def unlink(self):
        """Recompute depreciation when grant is deleted"""
        assets_to_recompute = self.mapped('account_asset_id').filtered(
            lambda a: a.state in ['open', 'close']
        )
        res = super().unlink()

        # Recompute using standard method (will use our override)
        for asset in assets_to_recompute:
            asset.compute_depreciation_board()

        return res