import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    deferred_count = fields.Integer(
        string='Deferred Entry Count',
        compute='_compute_deferred_count',
    )

    def _compute_deferred_count(self):
        for move in self:
            move.deferred_count = self.env['account.deferred'].search_count([
                ('move_id', '=', move.id),
            ])

    def action_open_deferred_wizard(self):
        """Open the deferred entry wizard for this move."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Deferred Entry'),
            'res_model': 'account.deferred.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'account.move',
            },
        }

    def action_post(self):
        """In booking model B (auto defer), park deferred-linked invoice lines on
        their interim/periodiserings account when the move is posted.

        Model A (explicit prepaid) leaves the invoice line account as the
        accountant coded it; only the release stubs are scheduled. In model B the
        net cost is moved off the expense/income account and onto the deferred
        (interim) account at posting, and the periodic releases then move it back
        to the expense account over time. VAT lines and unrelated lines are never
        touched.
        """
        lines_to_park = self._deferred_lines_to_park_on_post()
        if lines_to_park:
            lines_to_park.with_context(check_move_validity=True).write({
                'account_id': lines_to_park.deferred_id.account_depreciation_id.id,
            })
        return super().action_post()

    def _deferred_lines_to_park_on_post(self):
        """Return deferred-linked move lines that should be rebooked onto their
        interim account at posting under model B (auto defer).

        Only applies to lines that carry a `deferred_id` (a deferral was scheduled
        for them) whose account is not already the deferred interim account, on a
        draft move belonging to a company configured for B. In model A no line is
        rebooked.
        """
        lines = self.env['account.move.line']
        for move in self:
            if move.state != 'draft':
                continue
            if move.company_id.deferred_booking_method != 'B_auto_defer':
                continue
            deferred_lines = move.line_ids.filtered('deferred_id')
            for line in deferred_lines:
                interim = line.deferred_id.account_depreciation_id
                if not interim or line.account_id.id == interim.id:
                    continue
                lines |= line
        return lines

    def action_view_deferred_entries(self):
        """View all deferred entries linked to this move."""
        self.ensure_one()
        deferred = self.env['account.deferred'].search([
            ('move_id', '=', self.id),
        ])
        if len(deferred) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Deferred Entry'),
                'res_model': 'account.deferred',
                'view_mode': 'form',
                'res_id': deferred.id,
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Deferred Entries'),
            'res_model': 'account.deferred',
            'view_mode': 'list,form',
            'domain': [('move_id', '=', self.id)],
        }


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    deferred_id = fields.Many2one(
        'account.deferred', string='Deferred Entry',
        readonly=True, index=True,
        help="Deferred entry created from this line.",
    )

    def action_open_deferred_wizard(self):
        """Open the deferred entry wizard from a move line."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Deferred Entry'),
            'res_model': 'account.deferred.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.move_id.id,
                'active_model': 'account.move',
                'default_move_line_id': self.id,
            },
        }
