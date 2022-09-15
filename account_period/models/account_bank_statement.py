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
from odoo import api, fields, models, _, exceptions
from odoo.osv import expression
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    @api.model_create_multi
    def create(self, vals_list):
        _logger.warning("AccountBankStatementLine CREATE")
        for vals in vals_list:
            statement = self.env['account.bank.statement'].browse(vals['statement_id'])
            if statement.state != 'open' and self._context.get('check_move_validity', True):
                raise UserError(_("You can only create statement line in open bank statements."))
            if 'date' not in vals:
                vals['date'] = statement.date
            date = vals['date']
            _logger.warning(f"{date=}")
            try:
                date = datetime.strptime(date, "%Y-%m-%d")
            except TypeError:
                pass
            period = vals['period_id'] = self.env['account.period'].date2period(date).id
            if not period:
                date_formated = datetime.strftime(date, "%Y-%m-%d")
                raise UserError(_(f"There is no period for the date {date_formated}, please choose another date or "
                                  f"create a period for that date."))
            _logger.warning(f"{period=}")
        return super(AccountBankStatementLine, self).create(vals_list)
    
    
    
