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
"""Entry point from a depreciation line.

Adds a **Change Entry** button to each row of the depreciation table on the
asset form.  It opens ``asset.line.change.move``, which performs the
``move_id`` write with the ``allow_asset_line_update`` context that OCA's
guard requires.
"""

from odoo import _, models


class AccountAssetLine(models.Model):
    _inherit = 'account.asset.line'

    def action_open_change_move(self):
        """Open the wizard that changes this line's bound entry."""
        self.ensure_one()
        return {
            'name': _('Change entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'asset.line.change.move',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_asset_line_id': self.id,
                'default_operation': 'change' if self.move_id else 'change',
            },
        }
