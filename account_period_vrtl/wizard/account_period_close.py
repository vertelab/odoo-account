# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2017 Vertel AB (<http://vertel.se>).
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
from odoo import api, fields, models, _
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

import logging
_logger = logging.getLogger(__name__)


class AccountPeriodClose(models.TransientModel):
    """
        close period
    """
    _name = "account.period.close"
    _description = "period close"

    sure = fields.Boolean(string='Check this box')

    def data_save(self):
        """
        This function close period
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: account period close’s ID or list of IDs
         """
        period_pool = self.pool.get('account.period')
        account_move_obj = self.pool.get('account.move')

        mode = 'done'
        for form in self:
            if form['sure']:
                for id in self.env.context.get('active_ids', []):
                    self.env.cr.execute('update account_period set state=%s where id=%s', (mode, id))

        return {'type': 'ir.actions.act_window_close'}
