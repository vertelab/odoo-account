# Copyright 2024- Vertel AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountDeferredWizard(models.TransientModel):
    _name = 'account.deferred.wizard'
    _description = 'Create Deferred Entry Wizard'

    # ── Context ───────────────────────────────────────────────────────
    move_id = fields.Many2one(
        'account.move', string='Journal Entry', required=True,
        default=lambda self: self._default_move_id(),
    )
    company_id = fields.Many2one(
        'res.company', related='move_id.company_id',
    )
    company_currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id',
    )

    # ── Invoice tab ───────────────────────────────────────────────────
    move_line_id = fields.Many2one(
        'account.move.line', string='Invoice Line',
        domain="["
               "('move_id', '=', move_id), "
               "('display_type', 'not in', ['line_section', 'line_note']), "
               "('account_id', '!=', False)"
               "]",
        default=lambda self: self._default_move_line_id(),
    )
    profile_id = fields.Many2one(
        'account.deferred.profile', string='Template',
    )
    amount = fields.Monetary(
        string='Periodiseringsbelopp', required=True,
        currency_field='company_currency_id',
    )
    period_account_id = fields.Many2one(
        'account.account', string='Periodiseringskonto', required=True,
        domain="[('deprecated', '=', False)]",
        help='Balance sheet account for the deferral (e.g. 1710 / 2990).',
    )
    expense_account_id = fields.Many2one(
        'account.account', string='Kostnads-/intäktskonto', required=True,
        domain="[('deprecated', '=', False)]",
        help='P&L account receiving the periodic entries.',
    )

    # ── Schedule tab ──────────────────────────────────────────────────
    frequency = fields.Selection([
        ('month', 'Monthly'),
        ('quarter', 'Quarterly'),
        ('year', 'Yearly'),
    ], string='Frequency', default='month', required=True)
    period_count = fields.Integer(
        string='Number of Periods', required=True, default=12,
    )
    start_date = fields.Date(
        string='Start Date', required=True,
        default=lambda self: self._default_start_date(),
    )
    notes = fields.Text(string='Notes')

    # ── Defaults ──────────────────────────────────────────────────────

    @api.model
    def _default_move_id(self):
        ctx = self.env.context
        if ctx.get('active_model') == 'account.move.line' and ctx.get('active_id'):
            line = self.env['account.move.line'].browse(ctx['active_id'])
            return line.move_id.id
        return ctx.get('active_id')

    @api.model
    def _default_move_line_id(self):
        ctx = self.env.context
        if ctx.get('active_model') == 'account.move.line' and ctx.get('active_id'):
            return ctx['active_id']
        return ctx.get('default_move_line_id')

    @api.model
    def _default_start_date(self):
        move_id = self._default_move_id()
        if move_id:
            move = self.env['account.move'].browse(move_id)
            return move.invoice_date or move.date or fields.Date.today()
        return fields.Date.today()

    # ── Onchanges ─────────────────────────────────────────────────────

    @api.onchange('move_line_id')
    def _onchange_move_line_id(self):
        if self.move_line_id:
            self.amount = abs(self.move_line_id.balance)
            if self.move_line_id.name:
                self.notes = self.move_line_id.name
            # Auto-set template from product and cascade its defaults
            product = self.move_line_id.product_id
            if product and product.deferred_profile_id:
                self.profile_id = product.deferred_profile_id
                self._onchange_profile_id()

    @api.onchange('profile_id')
    def _onchange_profile_id(self):
        if self.profile_id:
            self.frequency = self.profile_id.method_period
            self.period_count = self.profile_id.method_number
            self.period_account_id = self.profile_id.account_depreciation_id
            # Profile's expense account is authoritative (use_line_account removed)
            self.expense_account_id = self.profile_id.account_expense_id

    # ── Wizard action ─────────────────────────────────────────────────

    def action_create(self):
        self.ensure_one()
        if not self.move_line_id:
            raise UserError(_('Please select an account move line.'))
        if self.amount <= 0:
            raise UserError(_('The amount must be positive.'))
        if self.period_count <= 0:
            raise UserError(_('Number of periods must be at least 1.'))
        if not self.profile_id:
            raise UserError(_('No accrual template found. Set one on the product or select a template.'))

        # T/11321 #1/#4: never silently periodise the same invoice line twice.
        if self.move_line_id.deferred_id:
            raise UserError(_(
                'This invoice line has already been periodised in the deferred '
                'entry "%(name)s". Create a deferred entry from another line or '
                'reuse the existing one.'
            ) % {'name': self.move_line_id.deferred_id.name})

        profile = self.profile_id

        # REQ-3: the analytic distribution travels with the origin line when it
        # carries one; the profile value is only a fallback.
        analytic_distribution = (self.move_line_id.analytic_distribution
                                 or profile.analytic_distribution
                                 or False)

        deferred_vals = {
            'name': self.notes or self.move_line_id.name or _('Deferred Entry'),
            'code': self.move_id.name,
            'profile_id': profile.id,
            'rec_type': profile.rec_type,
            'partner_id': self.move_line_id.partner_id.id or self.move_id.partner_id.id,
            'company_id': self.company_id.id,
            'account_depreciation_id': self.period_account_id.id,
            # T/11321 #7: honour the account the accountant picked in the wizard.
            # The profile value is only the onchange default, not a forcing rule.
            'account_expense_id': (self.expense_account_id.id
                                   or profile.account_expense_id.id),
            'journal_id': profile.journal_id.id,
            'amount_total': self.amount,
            'date_start': self.start_date,
            'method_period': self.frequency,
            'method_number': self.period_count,
            'allow_reversal': profile.allow_reversal,
            'analytic_distribution': analytic_distribution,
            'move_line_id': self.move_line_id.id,
            'state': 'open' if profile.open_asset else 'draft',
        }
        deferred = self.env['account.deferred'].create(deferred_vals)

        # Link back to the origin line
        self.move_line_id.deferred_id = deferred.id

        # Generate stubs
        deferred._generate_stubs()

        # Chatter message
        msg = _(
            'Deferred entry created: <a href=# data-oe-model=account.deferred '
            'data-oe-id=%(deferred_id)s>%(name)s</a> '
            '(%(amount)s over %(periods)s %(freq)s)'
        ) % {
            'deferred_id': deferred.id,
            'name': deferred.name,
            'amount': self._format_amount(self.amount),
            'periods': self.period_count,
            'freq': dict(self._fields['frequency'].selection).get(self.frequency, ''),
        }
        self.move_id.message_post(body=msg)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Deferred Entry'),
            'res_model': 'account.deferred',
            'view_mode': 'form',
            'res_id': deferred.id,
            'target': 'current',
        }

    def _format_amount(self, amount):
        company = self.company_id
        if company.currency_id:
            return company.currency_id.format(amount)
        return str(amount)
