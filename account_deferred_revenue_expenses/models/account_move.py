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
