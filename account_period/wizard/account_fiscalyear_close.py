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
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class account_period_close(models.TransientModel):
    """
        close period
    """
    _name = "account.fiscalyear.close"
    _description = "fiscalyear close"

    sure = fields.Boolean(string='Check this box')

    def data_save(self):
        """
        This function close fiscalyear
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: account period close’s ID or list of IDs
         """
        for form in self:
            if form['sure']:
                for rec in self.env.context.get('active_ids', []):
                    fis_year = self.env["account.fiscalyear"].browse(rec)
                    for period in fis_year.period_ids:
                        if period.state == "draft":
                            raise UserError(_('You can not close fiscalyear with that has a period that is opened, '
                                              'please close period'))
                    fis_year.state = "done"

        return {'type': 'ir.actions.act_window_close'}
