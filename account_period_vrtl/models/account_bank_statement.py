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


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    def _period_id(self):
        return self.env['account.period'].date2period(self.date or fields.Date.today()).id

    period_id = fields.Many2one(comodel_name='account.period', string='Period', default=_period_id)

    @api.model_create_multi
    def create(self, values):
        for val in values:
            if not "period_id" in values:
                val['period_id'] = self.env['account.period'].date2period(val.get('date') or fields.Date.today()).id
        res = super(AccountBankStatement, self).create(values)
        return res


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'date' in vals:
                date = vals['date']
                try:
                        date = datetime.strptime(date, "%Y-%m-%d")
                except TypeError:
                        pass
                period = vals['period_id'] = self.env['account.period'].date2period(date).id
                if not period:
                        date_formated = datetime.strftime(date, "%Y-%m-%d")
                        raise UserError(_(
                            f"There is no period for the date {date_formated}, please choose another date or "
                            "create a period for that date."
                        ))
        return super(AccountBankStatementLine, self).create(vals_list)
