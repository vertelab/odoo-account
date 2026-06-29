# Copyright 2024- Vertel AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class AccountDeferredProfile(models.Model):
    _name = 'account.deferred.profile'
    _description = 'Deferred Entry Profile'
    _inherit = ['analytic.mixin']
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company,
    )
    rec_type = fields.Selection([
        ('deferred_expense', 'Deferred Expense'),
        ('deferred_income', 'Deferred Income'),
    ], string='Type', required=True, default='deferred_expense')

    # ── Accounts ──────────────────────────────────────────────────────
    account_depreciation_id = fields.Many2one(
        'account.account', string='Periodiseringskonto',
        domain="[('deprecated', '=', False)]",
        check_company=True, required=True,
        help="Balance sheet account (e.g. 1710 for prepaid, 2990 for deferred income).",
    )
    account_expense_id = fields.Many2one(
        'account.account', string='Expense/Income Account',
        domain="[('deprecated', '=', False)]",
        check_company=True,
        help="P&L account (e.g. 5010 for expense, 3010 for income).",
    )
    use_line_account = fields.Boolean(
        string='Use line account', default=True,
        help='When creating a deferred entry: if checked, the expense/income '
             'account is taken from the invoice line. '
             'If unchecked, this template\'s account overwrites the line account.',
    )
    journal_id = fields.Many2one(
        'account.journal', string='Journal',
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        check_company=True, required=True,
    )

    # ── Periodization defaults ────────────────────────────────────────
    method_period = fields.Selection([
        ('month', 'Monthly'),
        ('quarter', 'Quarterly'),
        ('year', 'Yearly'),
    ], string='Period Length', required=True, default='month')
    method_number = fields.Integer(
        string='Number of Periods', required=True, default=12,
    )
    open_asset = fields.Boolean(
        string='Skip Draft State', default=True,
        help="Automatically confirm the deferred entry when created.",
    )
    allow_reversal = fields.Boolean(
        string='Allow Reversal',
        help="If set, posted moves can be reversed instead of deleted.",
    )

    # ── Notes ─────────────────────────────────────────────────────────
    note = fields.Text()

    def _get_deferred_vals(self):
        """Return common values to copy onto an account.deferred."""
        self.ensure_one()
        return {
            'profile_id': self.id,
            'rec_type': self.rec_type,
            'account_depreciation_id': self.account_depreciation_id.id,
            'account_expense_id': self.account_expense_id.id,
            'journal_id': self.journal_id.id,
            'method_period': self.method_period,
            'method_number': self.method_number,
            'analytic_distribution': self.analytic_distribution,
            'allow_reversal': self.allow_reversal,
        }
