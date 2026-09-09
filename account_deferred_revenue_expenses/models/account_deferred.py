# Copyright 2024- Vertel AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

import logging
import math
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountDeferred(models.Model):
    _name = 'account.deferred'
    _description = 'Deferred Entry'
    _order = 'id desc'
    _check_company_auto = True
    _inherit = ['mail.thread', 'analytic.mixin']

    # ── Identification ────────────────────────────────────────────────
    name = fields.Char(string='Description', required=True)
    code = fields.Char(string='Reference')
    profile_id = fields.Many2one(
        'account.deferred.profile', string='Profile',
        check_company=True, required=True,
    )
    rec_type = fields.Selection([
        ('deferred_expense', 'Deferred Expense'),
        ('deferred_income', 'Deferred Income'),
    ], string='Type', required=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id',
    )

    # ── Accounts (snapshot from profile at creation) ──────────────────
    account_depreciation_id = fields.Many2one(
        'account.account', string='Periodiseringskonto',
        check_company=True, required=True,
    )
    account_expense_id = fields.Many2one(
        'account.account', string='Expense/Income Account',
        check_company=True, required=True,
    )
    journal_id = fields.Many2one(
        'account.journal', string='Journal',
        check_company=True, required=True,
    )

    # ── Origin (link back to the invoice line) ────────────────────────
    move_line_id = fields.Many2one(
        'account.move.line', string='Origin Line',
        readonly=True,
    )
    move_id = fields.Many2one(
        'account.move', string='Origin Move',
        related='move_line_id.move_id', store=True, readonly=True,
    )

    # ── Amounts & Schedule ────────────────────────────────────────────
    amount_total = fields.Monetary(
        string='Total Amount', required=True,
        currency_field='currency_id',
    )
    date_start = fields.Date(string='Start Date', required=True)
    method_period = fields.Selection([
        ('month', 'Monthly'),
        ('quarter', 'Quarterly'),
        ('year', 'Yearly'),
    ], string='Period Length', required=True, default='month')
    method_number = fields.Integer(
        string='Number of Periods', required=True, default=12,
    )
    allow_reversal = fields.Boolean(string='Allow Reversal')


    # ── Lines (stubbar) ───────────────────────────────────────────────
    line_ids = fields.One2many(
        'account.deferred.line', 'deferred_id',
        string='Periodization Stubs',
    )
    line_count = fields.Integer(
        compute='_compute_line_counts', string='# Stubs',
    )
    posted_count = fields.Integer(
        compute='_compute_line_counts', string='# Posted',
    )

    # ── State ─────────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Running'),
        ('close', 'Closed'),
    ], string='Status', default='draft', required=True, tracking=True)
    value_residual = fields.Monetary(
        compute='_compute_residual', string='Remaining',
        currency_field='currency_id',
    )

    # ── Computes ──────────────────────────────────────────────────────

    def _compute_line_counts(self):
        for r in self:
            r.line_count = len(r.line_ids)
            r.posted_count = len(r.line_ids.filtered('posted'))

    def _compute_residual(self):
        for r in self:
            posted_total = sum(
                r.line_ids.filtered('posted').mapped('amount'))
            r.value_residual = r.amount_total - posted_total

    # ── Actions ───────────────────────────────────────────────────────

    def action_confirm(self):
        """Confirm deferred entry — generates stubs if not yet generated."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft entries can be confirmed.'))
            if not rec.line_ids:
                rec._generate_stubs()
            rec.state = 'open'

    def action_close(self):
        self.state = 'close'

    def action_draft(self):
        self.state = 'draft'

    # ── Schedule wizards ────────────────────────────────────────────────

    @api.onchange('date_start', 'method_period', 'method_number')
    def _onchange_schedule(self):
        """T/11321 #3: live re-sync of the not-yet-posted stubs on the form.

        We only warn when it cannot be done automatically (something is already
        booked); the actual rebuild happens on save via :meth:`write`. Keeping the
        work in ``write`` (instead of an onchange returning a ``line_ids`` cmd
        list) gives a reliable round-trip through the ORM — an onchange cannot
        reliably replace rows of an embedded ``list`` that sits on a different
        notebook page in Odoo 18.
        """
        if self.line_ids.filtered('posted'):
            warning = {
                'title': _('Some stubs are already posted'),
                'message': _(
                    'Changing the schedule is not applied to the posted stubs. '
                    'Only the not-yet-posted stubs will be regenerated when you '
                    'save.'),
            }
            return {'warning': warning}

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if any(f in vals for f in ('date_start', 'method_period', 'method_number')):
                # Only re-plan on real entries that actually carry stubs.
                if rec.id and rec.line_ids:
                    rec._generate_stubs()
        return res

    def _generate_stubs(self):
        """Rebuild the not-yet-posted stubs from the schedule on ``self``.

        Keeps any posted stub (already booked) untouched and only regenerates the
        open rows. Safe to re-run — used at creation (wizard/confirm), when the
        schedule fields are edited on a saved entry (``write``) and by the manual
        re-plan action.
        """
        self.ensure_one()
        if not self.date_start or not self.method_number:
            return
        posted = self.line_ids.filtered('posted')
        self.line_ids = ([(6, 0, posted.ids)] if posted else [(5, 0, 0)])\
            + self._new_stub_vals()

    def _new_stub_vals(self):
        """Compute the ``(0,0,vals)`` commands for the schedule on ``self``."""
        self.ensure_one()
        delta_map = {'month': 'months', 'quarter': 'months', 'year': 'years'}
        period_amount = self.amount_total / self.method_number
        period_amount = self.currency_id.round(period_amount)
        residual = self.amount_total - (period_amount * self.method_number)

        vals = []
        for i in range(self.method_number):
            if self.method_period == 'quarter':
                date = self.date_start + relativedelta(months=3 * i)
            else:
                date = self.date_start + relativedelta(**{delta_map[self.method_period]: i})
            amount = period_amount
            if i == self.method_number - 1 and residual:
                amount = self.currency_id.round(amount + residual)
            vals.append((0, 0, {
                'name': _('Period %d/%d') % (i + 1, self.method_number),
                'sequence': (i + 1) * 10,
                'date': date,
                'amount': amount,
            }))
        return vals



    def action_open_stubs(self):
        """Smart button: open stubs tree."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Periodization Stubs'),
            'res_model': 'account.deferred.line',
            'view_mode': 'list,form',
            'domain': [('deferred_id', '=', self.id)],
            'context': {
                'default_deferred_id': self.id,
            },
        }

    def action_post_all_stubs(self):
        """Post all unposted stubs up to a given date."""
        self.ensure_one()
        posted = 0
        for stub in self.line_ids.filtered(lambda l: not l.posted):
            stub.action_create_move()
            posted += 1
        if posted:
            self._compute_residual()
            _check_close = self.value_residual == 0.0
            if _check_close:
                self.state = 'close'
        return True

    def _cron_post_due_stubs(self):
        """Daily job (independent of month-end closing): post every release stub
        that is due on or before today for running (``open``) deferred entries.

        Each stub is posted through the normal posting engine
        (``action_create_move`` -> ``account.move.action_post``), so account/period
        locks are respected automatically. When a due stub falls in a locked or
        closed period, posting raises a ``UserError``; the stub is then left
        unposted and the run continues, so a lock never fails the whole job or
        creates an entry in a closed period.
        """
        today = fields.Date.today()
        entries = self.search([('state', '=', 'open')])
        for deferred in entries:
            due_stubs = deferred.line_ids.filtered(
                lambda l: not l.posted and l.date <= today)
            for stub in due_stubs:
                try:
                    stub.action_create_move()
                except UserError as e:
                    # Locked/closed period or another posting constraint: leave
                    # the stub unposted and keep going.
                    _logger.warning(
                        'Deferred %s stub not posted by daily job (date %s): %s',
                        deferred.name, stub.date, e)
                    continue
            if due_stubs:
                deferred._compute_residual()
                if deferred.value_residual == 0.0:
                    deferred.state = 'close'
        return True

    # ── Link to origin ────────────────────────────────────────────────

    def action_open_origin_move(self):
        self.ensure_one()
        move = self.move_id or self.move_line_id.move_id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
        }
