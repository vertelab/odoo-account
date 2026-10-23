# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<https://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""Entry point from the journal entry form.

Adds ``action_open_relink_asset`` to ``account.move``.  The button that used
to call it was removed from the journal entry form — re-linking is done from
the asset side (``asset.relink.move`` is still reachable through
``asset.line.change.move`` and ``action_match_moves``).

The method is kept so the wizard remains callable from server actions and
tests, and so an existing deployment that still has the button in a stale
view does not break.
"""

from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_open_relink_asset(self):
        """Open the re-link wizard for this entry."""
        self.ensure_one()
        if not self.line_ids.filtered('asset_id'):
            raise UserError(_(
                'This journal entry has no lines linked to an asset.'))
        return {
            'name': _('Re-link asset'),
            'type': 'ir.actions.act_window',
            'res_model': 'asset.relink.move',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_id': self.id,
            },
        }
