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
from odoo.exceptions import Warning

import logging
_logger = logging.getLogger(__name__)


class AccountPeriodCreate(models.Model):
    _name = 'account.period.create.wizard'
    _description = 'Added period for accounting. Either 12 months or 4 quarters.'

    @api.model
    def default_fy_name(self):
        return fields.Date.today()[:4]

    @api.model
    def default_date_start(self):
        return '%s-01-01' %fields.Date.today()[:4]

    @api.model
    def default_date_stop(self):
        return '%s-12-31' %fields.Date.today()[:4]

    fy_name = fields.Char(string='Fiscal Year Name', required=True, default=default_fy_name)
    fy_code = fields.Char(string='Fiscal Year Code', required=True, default=default_fy_name)
    date_start = fields.Date(string='Start of Period', default=default_date_start, required=True)
    date_stop = fields.Date(string='End of Period',  default=default_date_stop, required=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get('account.account'))

    def create_period3(self):
        return self.create_period(interval=3)

    def create_period1(self): # Looks stupid right? But it looks like calling create_period() directly does not work
        return self.create_period(interval=1)

    def create_period(self, interval=1):
        if self.date_stop > self.date_start:
            fy = self.env['account.fiscalyear'].create({
                'name': self.fy_name,
                'code': self.fy_code,
                'company_id': self.company_id.id,
                'date_start': self.date_start,
                'date_stop': self.date_stop,
                'state': 'draft',
            })
            ds = datetime.strptime(self.date_start, '%Y-%m-%d')
            periods = []
            while ds.strftime('%Y-%m-%d') < self.date_stop:
                de = ds + relativedelta(months=interval, days=-1)
                if de.strftime('%Y-%m-%d') > self.date_stop:
                    de = datetime.strptime(self.date_stop, '%Y-%m-%d')
                period = self.env['account.period'].create({
                    'name': ds.strftime('%m/%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'fiscalyear_id': fy.id,
                })
                periods.append(int(period))
                ds = ds + relativedelta(months=interval)
            action = self.env['ir.actions.act_window'].for_xml_id('account_period', 'action_account_period_form')
            action['domain'] = [('id', 'in', periods)]
            return action
        else:
            raise Warning('Invalid Period!')
        return True
