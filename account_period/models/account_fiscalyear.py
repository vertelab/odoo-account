from odoo import api, fields, models, _, exceptions
from odoo.osv import expression
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError, Warning

import logging

_logger = logging.getLogger(__name__)

FIELDS = ['move_type','name','partner_id','invoice_date','journal_id','invoice_line_ids','line_ids','company_id','state']


class AccountFiscalyear(models.Model):
    _name = 'account.fiscalyear'
    _description = 'Fiscal Year'
    _order = 'date_start, id'

    def action_draft(self):
        for years in self:
            years.state = "draft"

    @api.model
    def default_date_start(self):
        return '%s-01-01' % fields.Date.today().strftime('%Y')

    @api.model
    def default_date_stop(self):
        return '%s-12-31' % fields.Date.today().strftime('%Y')

    @api.model
    def create(self, vals):
        res = super(AccountFiscalyear, self).create(vals)
        self.env.company.sudo().set_onboarding_step_done('account_setup_fy_data_state')
        return res

    name = fields.Char(string='Fiscal Year', required=True)
    code = fields.Char(string='Code', size=6, required=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', required=True,
                                 default=lambda self: self.env['res.company']._company_default_get('account.account'))
    date_start = fields.Date(string='Start Date', default=default_date_start, required=True)
    date_stop = fields.Date(string='End Date', default=default_date_stop, required=True)
    period_ids = fields.One2many(comodel_name='account.period', inverse_name='fiscalyear_id', string='Periods')
    state = fields.Selection([('draft', 'Open'), ('done', 'Closed')], string='Status', readonly=True, copy=False,
                             default='draft')

    def _check_duration(self):
        if self.date_stop < self.date_start:
            return False
        return True

    _constraints = [
        (_check_duration, 'Error!\nThe start date of a fiscal year must precede its end date.',
         ['date_start', 'date_stop'])
    ]

    def _set_state(self):
        for record in self:
            state = "done"
            for period in self.period_ids:
                if period.state == "draft":
                    state = "draft"
                    break
            record.state = state

    def create_period3(self):
        return self.create_period(3)

    def create_period1(self):  # very stupid that I need this!
        return self.create_period(1)

    def create_period(self, interval=1):
        for fy in self:
            ds = fy.date_start
            self.env['account.period'].create({
                'name': "%s %s" % (_('Opening Period'), ds.strftime('%Y')),
                'code': ds.strftime('00/%Y'),
                'date_start': ds.strftime('%Y-%m-%d'),
                'date_stop': ds.strftime('%Y-%m-%d'),
                'special': True,
                'fiscalyear_id': fy.id,
                'company_id': self.env.company.id
            })
            while ds < fy.date_stop:
                de = ds + relativedelta(months=interval, days=-1)

                if de > fy.date_stop:
                    de = fy.date_stop

                self.env['account.period'].create({
                    'name': ds.strftime('%m/%Y'),
                    'code': ds.strftime('%m/%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'fiscalyear_id': fy.id,
                    'company_id': self.env.company.id
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
            dt = fields.Date.context_today()
        args = [
            ('date_start', '<=', dt),
            ('date_stop', '>=', dt),
            ('company_id', '=', self.env.context.get('company_id',
                                                     self.env['res.company']._company_default_get('account.account')))]
        ids = self.env['account.fiscalyear'].search(args).mapped('id')
        if not ids:
            if exception:
                model, action_id = self.env['ir.model.data'].get_object_reference('account',
                                                                                  'action_account_fiscalyear')
                msg = _(
                    'There is no period defined for this date: %s.\nPlease go to Configuration/Periods and configure '
                    'a fiscal year.') % dt
                raise exceptions.RedirectWarning(msg, action_id, _('Go to the configuration panel'))
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
        return ids.name_get()

    def action_draft(self):
        mode = 'draft'
        for fiscalyear in self:
            fiscalyear.state = mode
        return True