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

FIELDS = ['move_type','name','partner_id','invoice_date','journal_id','invoice_line_ids','line_ids','company_id','state']

class AccountPeriod(models.Model):
    _name = 'account.period'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {'date.range': 'date_range_id'}
    _description = 'Period'
    _order = 'date_start, special desc'

    date_range_id = fields.Many2one('date.range', required=True, ondelete='cascade')

    account_period_journal_ids = fields.One2many('account.period.journal', 'period_id', string="Journals")

    @api.model
    def default_date_start(self):
        return '%s-01-01' % fields.Date.today().strftime('%Y')

    # date_start = fields.Date(string='Start of Period', default=default_date_start, required=True)

    @api.model
    def default_date_stop(self):
        return '%s-12-31' % fields.Date.today().strftime('%Y')

    date_stop = fields.Date(related='date_range_id.date_end', string='End of Period', store=True, readonly=False)

    # name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', size=12)
    special = fields.Boolean(string='Opening/Closing Period', help='These periods can overlap.')
    fiscalyear_id = fields.Many2one(comodel_name='account.fiscalyear', string='Fiscal Year', required=True, index=True)
    state = fields.Selection([('draft', 'Open'), ('done', 'Closed')], string='Status', readonly=True, copy=False,
                             help='When monthly periods are created. The status is \'Draft\'. At the end of monthly '
                                  'period it is in \'Done\' status.', default='draft')
    closing_date = fields.Date(string='Closing Date', default=lambda self: self.env.company.period_closing_date)
    # journal_id = fields.Many2one('account.journal', string="Journal")

    _sql_constraints = [
        ('name_unique', 'unique(name,company_id)', 'Period for this company already exist!')
    ]

    @api.constrains('date_stop')
    def _check_year_limit(self):
        for obj_period in self:
            if obj_period.special:
                continue

            if obj_period.fiscalyear_id.date_stop < obj_period.date_stop or \
                    obj_period.fiscalyear_id.date_stop < obj_period.date_start or \
                    obj_period.fiscalyear_id.date_start > obj_period.date_start or \
                    obj_period.fiscalyear_id.date_start > obj_period.date_stop:
                raise ValidationError(_('Error!\nThe period is invalid. Either some periods are overlapping or the '
                                        'period\'s dates are not matching the scope of the fiscal year.'))

            pids = self.search([('date_stop', '>=', obj_period.date_start), ('date_start', '<=', obj_period.date_stop),
                                ('special', '=', False), ('id', '<>', obj_period.id)])
            for period in pids:
                if period.fiscalyear_id.company_id.id == obj_period.fiscalyear_id.company_id.id:
                    raise ValidationError(
                        _('Error!\nThe period is invalid. Either some periods are overlapping or the period\'s dates '
                          'are not matching the scope of the fiscal year.'))

    @api.constrains('date_stop', 'date_start')
    def _check_duration(self):
        for account in self:
            if account.date_stop < account.date_start:
                raise ValidationError(_('Error!\nThe duration of the Period(s) is/are invalid.'))

    @api.returns('self')
    def next(self, period, step):
        self.ensure_one()
        ids = self.search([('date_start', '>', period.date_start)]).mapped('id')
        if len(ids) >= step:
            return ids[step - 1]
        return False

    @api.returns('self')
    def prev(self):
        for period in self:
            return self.search([('date_start', '<', period.date_start)], order='date_start')[-1]
        return self

    @api.returns('self')
    def now(self):
        for period in self:
            return period.find()

    @api.returns('self')
    def find(self, dt=None, context=None, company_id=False):
        if not company_id:
            company_id = self.env.context.get('company_id', self.env.user.company_id.id)
        context = context or {}
        # self.ensure_one()
        if not dt:
            dt = fields.Date.context_today()
        args = [('date_start', '<=', dt), ('date_stop', '>=', dt),
                ('company_id', '=', company_id)]
        result = []
        if context.get('account_period_prefer_normal', True):
            # look for non-special periods first, and fallback to all if no result is found
            result = self.search(args + [('special', '=', False)])
        if not result:
            result = self.search(args)
        if not result:
            raise UserError(f"There is no period defined for this date: {args} \nPlease go to Configuration/Periods.")
        return result

    def action_draft(self):
        mode = 'draft'
        for period in self:
            if period.fiscalyear_id.state == 'done':
                raise UserError(_('You can not re-open a period which belongs to closed fiscal year'))
        self.env.cr.execute('update account_period set state=%s where id in %s', (mode, tuple(self.mapped('id')),))
        return True

    def write(self, vals):
        if 'company_id' in vals:
            move_lines = self.env['account.move'].search([('period_id', 'in', self.mapped('id'))])
            if move_lines:
                raise UserError(
                    _('This journal already contains items for this period, therefore you cannot modify its company '
                      'field.'))
        return super(AccountPeriod, self).write(vals)

    def build_ctx_periods(self, period_from_id, period_to_id):
        self.ensure_one()
        if period_from_id == period_to_id:
            return [period_from_id]
        period_from = self.browse(period_from_id)
        period_date_start = period_from.date_start
        company1_id = period_from.company_id.id
        period_to = self.browse(period_to_id)
        period_date_stop = period_to.date_stop
        company2_id = period_to.company_id.id
        if company1_id != company2_id:
            raise UserError(_('You should choose the periods that belong to the same company.'))
        if period_date_start > period_date_stop:
            raise UserError(_('Start period should precede then end period.'))

        # /!\ We do not include a criterion on the company_id field below, to allow producing consolidated reports
        # on multiple companies. It will only work when start/end periods are selected and no fiscal year is chosen.

        # for period from = january, we want to exclude the opening period (but it has same date_from, so we have to
        # check if period_from is special or not to include that clause or not in the search).
        if period_from.special:
            return self.search([('date_start', '>=', period_date_start), ('date_stop', '<=', period_date_stop)])
        return self.search(
            [('date_start', '>=', period_date_start), ('date_stop', '<=', period_date_stop), ('special', '=', False)])

    @api.model
    def get_period_ids(self, period_start, period_stop, special=False):
        # ~ if isinstance(period_start, basestring):
        if isinstance(period_start, str):
            period_start = self.env['account.period'].search([('name', '=', period_start)], limit=1)
            period_stop = self.env['account.period'].search([('name', '=', period_stop)], limit=1)
        if isinstance(period_start, int):
            period_start = self.env['account.period'].browse(period_start)
            period_stop = self.env['account.period'].browse(period_stop)
        if not (period_start and period_stop):
            return []
        if period_stop and period_stop.date_start < period_start.date_start:
            raise UserError('Stop period must be after start period')
        if period_stop and period_stop.date_start == period_start.date_start:
            return [period_start.id]
        else:
            return [r.id for r in self.env['account.period'].search(
                [('date_start', '>=', period_start.date_start), ('date_stop', '<=', period_stop.date_stop),
                 ('special', '=', special)])]

    @api.model
    def get_next_periods(self, last_period, length=3, special=False):
        # ~ if isinstance(last_period, basestring):
        if isinstance(last_period, str):
            last_period = self.env['account.period'].search([('name', '=', last_period)], limit=1)
        if isinstance(last_period, int):
            last_period = self.env['account.period'].browse(last_period)
        if not last_period:
            return None, None
        periods = self.env['account.period'].search(
            [('date_stop', '>', last_period.date_stop), ('special', '=', special)], order='date_stop', limit=length)
        return periods[0] if periods else None, periods[length - 1] if len(periods) >= length else None

    @api.model
    def period2month(self, period, short=True):
        # ~ if isinstance(period, basestring):
        if isinstance(period, str):
            period = self.env['account.period'].search([('name', '=', period)], limit=1)
        if isinstance(period, int):
            period = self.env['account.period'].browse(period)
        return fields.Date.from_string(period.date_start).strftime("%b" if short else "%B")

    def _normalize_date(self, date):
        if isinstance(date, str) and date:
            return datetime.strptime(date, "%Y-%m-%d")
        return date

    def _period_domain(self, date=None, journal_id=None, special=False):
        company_id = self.env.context.get('company_id') or self.env.company.id
        domain = [('special', '=', special), ('company_id', '=', company_id)]

        # if journal_id:
        #     domain.append(('journal_id', '=', journal_id.id))

        if date:
            date = self._normalize_date(date)
            date_str = date.strftime('%Y-%m-%d')
            domain += [('date_start', '<=', date_str), ('date_stop', '>=', date_str)]
        return domain
    
    @api.model
    def date2period(self, date):
        domain = self._period_domain(date=date)
        return self.env['account.period'].search(domain)

    # @api.model
    # def _get_period_by_journal(self, journal_id, date=None):
    #     domain = self._period_domain(date=date, journal_id=journal_id)
    #     return self.env['account.period'].search(domain)

    @api.depends("state")
    def _set_fiscalyear_id_state(self):
        for record in self:
            record.fiscalyear_id._set_state()

    @api.model
    def _cron_close_account_period(self):
        due_period_ids = self.search([('closing_date', '!=', False), ('closing_date', '<=', fields.Date.today())])
        if due_period_ids:
            due_period_ids.write({'state': 'done'})




class AccountPeriodJournal(models.Model):
    _name = 'account.period.journal'

    period_id = fields.Many2one('account.period', string='Period')
    journal_id = fields.Many2one('account.journal', string='Journals')
    closing_date = fields.Date(string="Closing Date")
    state = fields.Selection(
        [('draft', 'Open'), ('done', 'Closed')],
        string='Status',
        readonly=True, copy=False, default='draft'
    )


    def action_draft(self):
        mode = 'draft'
        for rec in self:
            if rec.period_id.state == 'done':
                raise UserError(_('You can not re-open a journal which belongs to closed period'))
        self.env.cr.execute('update account_period_journal set state=%s where id in %s', (mode, tuple(self.mapped('id')),))
        return True
