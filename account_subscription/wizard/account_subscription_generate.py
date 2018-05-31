# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2018 Vertel AB (<http://vertel.se>).
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import api, fields, models, _, exceptions
import time
from odoo.exceptions import Warning

import logging
_logger = logging.getLogger(__name__)


class account_subscription_generate(models.TransientModel):
    _name = "account.subscription.generate"
    _description = "Subscription Compute"

    date = fields.Date(string='Generate Entries Before', default=lambda *a: fields.Date.today(), required=True)

    @api.multi
    def action_generate(self):
        act_obj = self.env['ir.actions.act_window']
        sub_line_obj = self.env['account.subscription.line']
        moves_created = self.env['account.move'].browse()
        for data in self:
            lines = sub_line_obj.search([('date', '<', self.date), ('move_id', '=', False)])
            moves_created |= lines.move_create()
        action = self.env['ir.actions.act_window'].for_xml_id('account', 'action_move_journal_line')
        action.update({
            'domain': str([('id', 'in', moves_created._ids)]),
            'context': {},
        })
        return action
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': self.env.ref('account.view_move_tree').id,
            'target': 'current',
            'domain': str([('id', 'in', moves_created._ids)]),
            'context': {},
        }
