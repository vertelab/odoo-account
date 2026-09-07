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
        """In booking model A (cost-account entry), park deferred-linked invoice lines
        on their interim/periodiserings account when the move is posted.

        Model A (Visma-style): the bill is booked on the cost/expense account (the
        account the user entered, e.g. 5010). The module rebooks the deferred line to
        the interim account at posting so the net effect on the cost account is zero
        and the prepaid amount sits parked, then the daily cron releases it to the
        cost account over the profile periods. Model B (Fortnox-style) is coded
        directly on the interim account already, so no rebook is needed. VAT lines
        and unrelated lines are never touched in either model.
        """
        lines_to_park = self._deferred_lines_to_park_on_post()
        if lines_to_park:
            lines_to_park.with_context(check_move_validity=True).write({
                'account_id': lines_to_park.deferred_id.account_depreciation_id.id,
            })
        return super().action_post()

    def _deferred_lines_to_park_on_post(self):
        """Return deferred-linked move lines that should be parked onto their interim
        account at posting under model A (cost-account entry / Visma-style).

        In model A the deferred invoice line is coded on the cost/expense account, so
        we rebook it to the deferred interim account at posting to neutralise the P&L
        exposure and park the net cost. Only applies to lines carrying a `deferred_id`
        whose account is not already the deferred interim account, on a draft move of
        a company configured for model A. In model B (interim entry) the line is
        already on the interim account, so no line is returned.
        """
        lines = self.env['account.move.line']
        for move in self:
            if move.state != 'draft':
                continue
            if move.company_id.deferred_booking_method != 'A_visma_cost_entry':
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
