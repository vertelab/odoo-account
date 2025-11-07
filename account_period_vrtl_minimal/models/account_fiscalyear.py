from odoo import api, fields, models, _, exceptions
from odoo.osv import expression
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class AccountFiscalyear(models.Model):
    _name = 'account.fiscalyear'
    _description = 'Fiscal Year'
    _order = 'date_start, id'

    @api.model
    def default_date_start(self):
        return '%s-01-01' % fields.Date.today().strftime('%Y')

    @api.model
    def default_date_stop(self):
        return '%s-12-31' % fields.Date.today().strftime('%Y')

    name = fields.Char(string='Fiscal Year', required=True)
    code = fields.Char(string='Code', size=6, required=True)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    date_start = fields.Date(string='Start Date', default=default_date_start, required=True)
    date_stop = fields.Date(string='End Date', default=default_date_stop, required=True)
    period_ids = fields.One2many(comodel_name='account.period', inverse_name='fiscalyear_id', string='Periods')
    state = fields.Selection(
        [('draft', 'Open'), ('done', 'Closed')],
        string='Status',
        readonly=True,
        copy=False,
        default='draft'
    )
    date_range_type_id = fields.Many2one('date.range.type', string='Date Range Type', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        """Create date range type when fiscal year is created"""
        records = super().create(vals_list)
        for record in records:
            # Create a date range type for this fiscal year
            record.date_range_type_id = record._date_range_type()
        return records

    def _date_range_type(self):
        """Get or create the date range type for fiscal periods"""
        self.ensure_one()
        type_id = self.env['date.range.type'].search([
            ('name', '=', f'Fiscal Year {self.code}'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        if not type_id:
            type_id = self.env['date.range.type'].create({
                'name': f'Fiscal Year {self.code}',
                'allow_overlap': False,
                'company_id': self.company_id.id,
            })
        return type_id

    @api.constrains('date_start', 'date_stop')
    def _check_duration(self):
        for record in self:
            if record.date_start > record.date_stop:
                raise UserError('Error!\nThe start date of a fiscal year must precede its end date.')

    def _set_state(self):
        for record in self:
            state = "done"
            for period in record.period_ids:
                if period.state == "draft":
                    state = "draft"
                    break
            record.state = state

    def create_period3(self):
        return self.create_period(3)

    def create_period1(self):
        return self.create_period(1)

    def create_period(self, interval=1):
        for fy in self:
            # Ensure date range type exists
            if not fy.date_range_type_id:
                fy.date_range_type_id = fy._date_range_type()

            ds = fy.date_start

            # Opening period
            self.env['account.period'].create({
                'name': "%s %s" % (_('Opening Period'), ds.strftime('%Y')),
                'code': ds.strftime('00/%Y'),
                'date_start': ds.strftime('%Y-%m-%d'),
                'date_end': ds.strftime('%Y-%m-%d'),
                'special': True,
                'fiscalyear_id': fy.id,
                'company_id': fy.company_id.id,
                'type_id': fy.date_range_type_id.id,
            })

            # Regular periods
            while ds < fy.date_stop:
                de = ds + relativedelta(months=interval, days=-1)
                if de > fy.date_stop:
                    de = fy.date_stop

                self.env['account.period'].create({
                    'name': ds.strftime('%m/%Y'),
                    'code': ds.strftime('%m/%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_end': de.strftime('%Y-%m-%d'),
                    'fiscalyear_id': fy.id,
                    'company_id': fy.company_id.id,
                    'type_id': fy.date_range_type_id.id,
                })
                ds = ds + relativedelta(months=interval)
        return True

    @api.model
    def find(self, dt=None, exception=True):
        res = self.finds(dt, exception)
        return res and res[0] or False

    @api.model
    def finds(self, dt=None, exception=True):
        if not dt:
            dt = fields.Date.context_today(self)
        args = [
            ('date_start', '<=', dt),
            ('date_stop', '>=', dt),
            ('company_id', '=', self.env.context.get('company_id', self.env.company.id))
        ]
        ids = self.env['account.fiscalyear'].search(args).mapped('id')
        if not ids:
            if exception:
                raise UserError(
                    _('There is no fiscal year defined for this date: %s.\n'
                      'Please go to Configuration/Periods and configure a fiscal year.') % dt
                )
            else:
                return []
        return ids

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=80):
        if args is None:
            args = []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('code', operator, name), ('name', operator, name)]
        else:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        ids = self.search(expression.AND([domain, args]), limit=limit)
        return [(record.id, record.name) for record in ids]

    def action_draft(self):
        for fiscalyear in self:
            fiscalyear.state = 'draft'
        return True