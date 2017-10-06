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
import logging
_logger = logging.getLogger(__name__)


class AccountPeriod(models.Model):
    _name = 'account.period'

    @api.model
    def default_date_start(self):
        return '%s-01-01' %fields.Date.today()[:4]

    @api.model
    def default_date_stop(self):
        return '%s-12-31' %fields.Date.today()[:4]

    name = fields.Char(string='Name', required=True)
    date_start = fields.Date(string='Start of Period', default=default_date_start, required=True)
    date_stop = fields.Date(string='End of Period', default=default_date_stop, required=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get('account.account'))

    _sql_constraints = [
        ('name_unique',
        'unique(name)',
        'Period already exist!')
    ]
