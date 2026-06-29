# Copyright 2024- Vertel AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountDeferredLine(models.Model):
    _name = 'account.deferred.line'
    _description = 'Deferred Entry Stub'
    _order = 'date, sequence'
    _check_company_auto = True

    deferred_id = fields.Many2one(
        'account.deferred', string='Deferred Entry',
        required=True, ondelete='cascade', index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        'res.company', related='deferred_id.company_id', store=True,
    )
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id',
    )

    name = fields.Char(string='Label', readonly=True)
    sequence = fields.Integer(default=10)
    date = fields.Date(string='Date', required=True)
    amount = fields.Monetary(required=True, currency_field='currency_id')
    posted = fields.Boolean(
        string='Posted', default=False,
        help="A journal entry has been created for this stub.",
    )
    move_id = fields.Many2one(
        'account.move', string='Journal Entry',
        readonly=True, check_company=True,
    )

    # ── Actions ───────────────────────────────────────────────────────

    def action_create_move(self):
        """Create and post the periodization entry for this stub."""
        self.ensure_one()
        deferred = self.deferred_id
        if self.posted:
            raise UserError(_('This stub is already posted.'))

        move_vals = {
            'date': self.date,
            'ref': '%s — %s' % (deferred.code or deferred.name, self.name or ''),
            'journal_id': deferred.journal_id.id,
            'line_ids': [
                (0, 0, {
                    'name': deferred.name,
                    'account_id': deferred.account_depreciation_id.id,
                    'partner_id': deferred.partner_id.id,
                    'debit': 0.0 if self.amount >= 0 else -self.amount,
                    'credit': self.amount if self.amount >= 0 else 0.0,
                    'currency_id': deferred.currency_id.id,
                }),
                (0, 0, {
                    'name': deferred.name,
                    'account_id': deferred.account_expense_id.id,
                    'partner_id': deferred.partner_id.id,
                    'debit': self.amount if self.amount >= 0 else 0.0,
                    'credit': 0.0 if self.amount >= 0 else -self.amount,
                    'analytic_distribution': deferred.analytic_distribution or False,
                    'currency_id': deferred.currency_id.id,
                }),
            ],
        }
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        self.write({'move_id': move.id, 'posted': True})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_move(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_unlink_move(self):
        """Delete/reverse the move for this stub."""
        self.ensure_one()
        if not self.posted or not self.move_id:
            raise UserError(_('No posted move to unlink.'))

        deferred = self.deferred_id
        if deferred.allow_reversal:
            # Reverse instead of delete
            reverse_move = self.move_id._reverse_moves(
                [self.move_id], cancel=True)
            self.write({'posted': True, 'move_id': reverse_move.id})
        else:
            self.move_id.button_draft()
            self.move_id.with_context(
                force_delete=True).unlink()
            self.write({'posted': False, 'move_id': False})
        return True
