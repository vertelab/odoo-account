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


class AccountPeriod(models.Model):
    _name = 'account.period'
    _description = 'Period'
    _order = 'date_start, special desc'

    @api.model
    def default_date_start(self):
        return '%s-01-01' %fields.Date.today().strftime('%Y')
    date_start = fields.Date(string='Start of Period', default=default_date_start, required=True)
    @api.model
    def default_date_stop(self):
        return '%s-12-31' %fields.Date.today().strftime('%Y')
    date_stop = fields.Date(string='End of Period', default=default_date_stop, required=True)

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', size=12)
    special = fields.Boolean(string='Opening/Closing Period', help='These periods can overlap.')
    fiscalyear_id = fields.Many2one(comodel_name='account.fiscalyear', string='Fiscal Year', required=True, states={'done':[('readonly',True)]}, index=True)
    state = fields.Selection([('draft','Open'), ('done','Closed')], string='Status', readonly=True, copy=False, help='When monthly periods are created. The status is \'Draft\'. At the end of monthly period it is in \'Done\' status.', default='draft')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get('account.account'))

    _sql_constraints = [
        ('name_unique',
        'unique(name)',
        'Period already exist!')
    ]

    def _check_duration(self):
        if self[0].date_stop < self[0].date_start:
            return False
        return True

    def _check_year_limit(self):
        for obj_period in self:
            if obj_period.special:
                continue

            if obj_period.fiscalyear_id.date_stop < obj_period.date_stop or \
               obj_period.fiscalyear_id.date_stop < obj_period.date_start or \
               obj_period.fiscalyear_id.date_start > obj_period.date_start or \
               obj_period.fiscalyear_id.date_start > obj_period.date_stop:
                return False

            pids = self.search([('date_stop','>=',obj_period.date_start),('date_start','<=',obj_period.date_stop),('special','=',False),('id','<>',obj_period.id)])
            for period in pids:
                if period.fiscalyear_id.company_id.id==obj_period.fiscalyear_id.company_id.id:
                    return False
        return True

    _constraints = [
        (_check_duration, 'Error!\nThe duration of the Period(s) is/are invalid.', ['date_stop']),
        (_check_year_limit, 'Error!\nThe period is invalid. Either some periods are overlapping or the period\'s dates are not matching the scope of the fiscal year.', ['date_stop'])
    ]

    @api.returns('self')
    def next(self, period, step):
        self.ensure_one()
        ids = self.search([('date_start','>',period.date_start)]).mapped('id')
        if len(ids)>=step:
            return ids[step-1]
        return False

    @api.returns('self')
    def find(self, dt=None, context=None):
        self.ensure_one()
        if not dt:
            dt = fields.Date.context_today()
        args = [('date_start', '<=' ,dt), ('date_stop', '>=', dt), ('company_id', '=', self.env.context.get('company_id', self.env['res.company']._company_default_get('account.account')))]
        result = []
        if context.get('account_period_prefer_normal', True):
            # look for non-special periods first, and fallback to all if no result is found
            result = self.search(args + [('special', '=', False)])
        if not result:
            result = self.search(args)
        if not result:
            model, action_id = self.env['ir.model.data'].get_object_reference('account', 'action_account_period')
            msg = _('There is no period defined for this date: %s.\nPlease go to Configuration/Periods.') % dt
            raise exceptions.RedirectWarning(msg, action_id, _('Go to the configuration panel'))
        return result

    def action_draft(self):
        mode = 'draft'
        for period in self:
            if period.fiscalyear_id.state == 'done':
                raise UserError(_('You can not re-open a period which belongs to closed fiscal year'))
        self.env.cr.execute('update account_period set state=%s where id in %s', (mode, tuple(self.mapped('id')),))
        self.invalidate_cache()
        return True

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('code', operator, name), ('name', operator, name)]
        else:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        return self.search(expression.AND([domain, args]), limit=limit).name_get()

    def write(self, vals):
        if 'company_id' in vals:
            move_lines = self.enb['account.move.line'].search([('period_id', 'in', self.mapped('id'))])
            if move_lines:
                raise UserError(_('This journal already contains items for this period, therefore you cannot modify its company field.'))
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

        #for period from = january, we want to exclude the opening period (but it has same date_from, so we have to check if period_from is special or not to include that clause or not in the search).
        if period_from.special:
            return self.search([('date_start', '>=', period_date_start), ('date_stop', '<=', period_date_stop)])
        return self.search([('date_start', '>=', period_date_start), ('date_stop', '<=', period_date_stop), ('special', '=', False)])

    @api.model
    def get_period_ids(self, period_start, period_stop,special=False):
        # ~ if isinstance(period_start, basestring):
        if isinstance(period_start, str):
            period_start = self.env['account.period'].search([('name','=',period_start)],limit=1)
            period_stop = self.env['account.period'].search([('name','=',period_stop)],limit=1)
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
            return [r.id for r in self.env['account.period'].search([('date_start', '>=', period_start.date_start), ('date_stop', '<=', period_stop.date_stop), ('special', '=', special)])]

    @api.model
    def get_next_periods(self, last_period,length=3,special=False):
        # ~ if isinstance(last_period, basestring):
        if isinstance(last_period, str):
            last_period = self.env['account.period'].search([('name','=',last_period)],limit=1)
        if isinstance(last_period, int):
            last_period = self.env['account.period'].browse(last_period)
        if not last_period:
            return (None, None)
        periods =  self.env['account.period'].search([('date_stop','>',last_period.date_stop), ('special', '=', special)],order='date_stop',limit=length)
        return (periods[0] if periods else None,periods[length-1] if len(periods)>=length else None)

    @api.model
    def period2month(self, period,short=True):
        # ~ if isinstance(period, basestring):
        if isinstance(period, str):
            period = self.env['account.period'].search([('name','=',period)],limit=1)
        if isinstance(period, int):
            period = self.env['account.period'].browse(period)
        return fields.Date.from_string(period.date_start).strftime("%b" if short else "%B")

    @api.model
    def date2period(self, date):
        return self.env['account.period'].search([('date_start', '<=', date.strftime('%Y-%m-%d')), ('date_stop', '>=', date.strftime('%Y-%m-%d')), ('special', '=', False)])
    
    @api.depends("state")
    def _set_fiscalyear_id_state(self):
        _logger.warning("account_period running in the 1990s !!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        for record in self:
            record.fiscalyear_id._set_state()


class AccountFiscalyear(models.Model):
    _name = 'account.fiscalyear'
    _description = 'Fiscal Year'
    _order = 'date_start, id'
    
    def action_draft(self):
        for years in self:
            years.state = "draft"

    @api.model
    def default_date_start(self):
        return '%s-01-01' %fields.Date.today().strftime('%Y')

    @api.model
    def default_date_stop(self):
        return '%s-12-31' %fields.Date.today().strftime('%Y')

    @api.model
    def create(self, vals):
        res = super(AccountFiscalyear, self).create(vals)
        self.env.company.sudo().set_onboarding_step_done('account_setup_fy_data_state')
        return res

    name = fields.Char(string='Fiscal Year', required=True)
    code = fields.Char(string='Code', size=6, required=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', required=True, default=lambda self: self.env['res.company']._company_default_get('account.account'))
    date_start = fields.Date(string='Start Date', default=default_date_start, required=True)
    date_stop = fields.Date(string='End Date', default=default_date_stop, required=True)
    period_ids = fields.One2many(comodel_name='account.period', inverse_name='fiscalyear_id', string='Periods')
    state = fields.Selection([('draft','Open'), ('done','Closed')], string='Status', readonly=True, copy=False, default='draft')

    def _check_duration(self):
        if self.date_stop < self.date_start:
            return False
        return True

    _constraints = [
        (_check_duration, 'Error!\nThe start date of a fiscal year must precede its end date.', ['date_start','date_stop'])
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

    def create_period1(self): #very stupid that I need this!
        return self.create_period(1)

    def create_period(self, interval=1):
        for fy in self:
            ds = fy.date_start
            self.env['account.period'].create({
                    'name':  "%s %s" % (_('Opening Period'), ds.strftime('%Y')),
                    'code': ds.strftime('00/%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': ds.strftime('%Y-%m-%d'),
                    'special': True,
                    'fiscalyear_id': fy.id,
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
        args = [('date_start', '<=' ,dt), ('date_stop', '>=', dt), ('company_id', '=', self.env.context.get('company_id', self.env['res.company']._company_default_get('account.account')))]
        ids = self.env['account.fiscalyear'].search(args).mapped('id')
        if not ids:
            if exception:
                model, action_id = self.env['ir.model.data'].get_object_reference('account', 'action_account_fiscalyear')
                msg = _('There is no period defined for this date: %s.\nPlease go to Configuration/Periods and configure a fiscal year.') % dt
                raise openerp.exceptions.RedirectWarning(msg, action_id, _('Go to the configuration panel'))
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
        for  fiscalyear in self:
            fiscalyear.state = mode
        return True


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def validate_open_period(self, values):
        period_id = self.env['account.period'].browse(values.get('period_id'))
        if period_id and period_id.state == 'done':
            raise ValidationError(_("You have tried to create an invoice on a closed period {period_id.name}.\n Please change period or open {period_id.name}").format(**locals()))
    
    def write(self, values):
        if isinstance(values, list):
            for i in range(len(values)):
                self.validate_open_period(values[i])
        else:
            self.validate_open_period(values)
        return super(AccountMove, self).write(values)
        
    @api.model_create_multi
    def create(self, values):
        if isinstance(values, list):
            for i in range(len(values)):
                self.validate_open_period(values[i])
        else:
            self.validate_open_period(values)
        return  super(AccountMove, self).create(values)
        
    def _get_default_period_id(self):
        return self.env['account.period'].date2period(self.invoice_date or fields.Date.today())
        
    period_id = fields.Many2one(
        comodel_name='account.period', string='Period', default=_get_default_period_id,
        required=True, states={'posted':[('readonly',True)]}, domain="[('state', '!=', 'done')]")

    payment_period_id = fields.Many2one(store=True, comodel_name='account.period', string='Payment Invoice Period', compute="_set_period_from_payment", readonly=True)
    payment_date = fields.Date(store=True, string='Invoice Payment Date', compute="_set_date_from_payment", readonly=True)
    payment_move_id = fields.Many2one(store=True,comodel_name='account.move', string='The payment invoice', compute="_set_payment_invoice", readonly=True)

    @api.depends("payment_move_id.period_id","payment_move_id")
    def _set_period_from_payment(self):
        for rec in self:
            if rec.payment_move_id:
                rec.payment_period_id = rec.payment_move_id.period_id
            else:
                rec.payment_period_id = False

    @api.depends("payment_move_id.date","payment_move_id")
    def _set_date_from_payment(self):
        for rec in self:
            if rec.payment_move_id:
                rec.payment_date = rec.payment_move_id.date
            else:
                rec.payment_date = False

    @api.depends("payment_state","state")
    def _set_payment_invoice(self):
        for rec in self:
            if rec.state == 'posted' and rec.is_invoice(include_receipts=True) and rec.payment_state == 'paid':
                # Used when searching for account_moves using the cash method with mis_builder. Currently it's linking the latest payment account.move so that the mis_instance can search using its period or date.
                #I'm not sure how to handle multiple payments which is why im only linking the latest one.
                list_of_payments = rec._get_reconciled_info_JSON_values()
                if list_of_payments:
                    latest_payment = self.env[ 'account.move'].search([('id', '=', list_of_payments[0]['move_id'])], limit=1)
                    for payment in list_of_payments:
                        current_payment = self.env[ 'account.move'].search([('id', '=', payment['move_id'])], limit=1)
                        if current_payment.period_id.date_stop > latest_payment.period_id.date_stop:
                            latest_payment = current_payment
                        rec.payment_move_id = latest_payment
                else:
                    rec.payment_move_id = False
            else:
                rec.payment_move_id = False
                
    @api.onchange("invoice_date")
    def set_period_based_on_invoice_date(self):
        if self.invoice_date:
            period_id = self.env['account.period'].date2period(self.invoice_date)
            if period_id and period_id.state == 'done':
                raise ValidationError(_("You have tried to create an invoice on a closed period {period_id.name}.\n Please change period or open {period_id.name}").format(**locals()))
            else:
                self.period_id = period_id
                
    def action_post(self):
        if self.period_id and self.period_id.state == 'done':
            raise ValidationError(_("You have tried to validate an invoice on a closed period {self.period_id.name}.\n Please change period or open {self.period_id.name}").format(**locals()))
        return super(AccountMove, self).action_post()




class account_account(models.Model):
    _inherit = 'account.account'

    def get_debit_credit_balance(self, period, target_move):
        self.ensure_one()
        if not target_move or target_move == 'all':
            target_move = ['draft', 'posted']
        else:
            target_move = [target_move]
        lines = self.env['account.move.line'].search([('move_id.period_id' ,'=', period.id), ('account_id', '=', self.id), ('move_id.state', 'in', target_move)]) # move lines with period_id
        return {
            'debit': sum(lines.mapped('debit')),
            'credit': sum(lines.mapped('credit')),
            'balance': sum(lines.mapped('debit')) - sum(lines.mapped('credit')),
        }

    def get_balance(self, period, target_move):
        self.ensure_one()
        return self.get_debit_credit_balance(period, target_move).get('balance')

    def sum_period(self):
        self.ensure_one()

        domain = [('move_id.period_id', 'in', self.env['account.period'].get_period_ids(self._context.get('period_start'), self._context.get('period_stop',self._context.get('period_start')))), ('account_id', '=', self.id)]
    
        if self._context.get('target_move') in ['draft', 'posted']:
            domain.append(('move_id.state', '=', self._context.get('target_move')))

        return sum([a.balance for a in self.env['account.move.line'].search(domain)])

class account_bank_statement(models.Model):
    _inherit = 'account.bank.statement'

    def _period_id(self):
        return self.env['account.period'].date2period(self.date or fields.Date.today()).id

    period_id = fields.Many2one(comodel_name='account.period', string='Period', default=_period_id)


# class account_abstract_payment(models.AbstractModel):
#     _inherit = "account.abstract.payment"
#
#     def _default_period_id(self):
#         return self.env['account.period'].date2period(self.payment_date or fields.Date.today()).id
#
#     payment_period_id = fields.Many2one(comodel_name='account.period', string='Period', default=_default_period_id)
#
#     @api.onchange('payment_date')
#     def onchange_payment_date_set_period_id(self):
#         self.payment_period_id = self.env['account.period'].date2period(self.payment_date or fields.Date.today())

# ~ class account_payment(models.Model):
    # ~ _inherit = "account.payment"

    # def _get_move_vals(self, journal=None):
    #     res = super(account_payment, self)._get_move_vals(journal)
    #     res['period_id'] = self.payment_period_id and self.payment_period_id.id
    #     return res

# class account_register_payments(models.TransientModel):
#     _inherit = "account.register.payments"
#
#     def get_payment_vals(self, journal=None):
#         res = super(account_register_payments, self).get_payment_vals()
#         res['payment_period_id'] = self.payment_period_id and self.payment_period_id.id
#         return res


# class AccountInvoice(models.Model):
#     _inherit = 'account.invoice'
#
#     def _get_default_period_id(self):
#         return self.env['account.period'].date2period(self.date_invoice or fields.Date.today()).id
#
#     period_id = fields.Many2one(comodel_name='account.period', string='Period', default=_get_default_period_id)
#
#     @api.onchange('date_invoice')
#     def onchange_date_set_period(self):
#         self.period_id = self.env['account.period'].date2period(self.date_invoice or fields.Date.today())
#
#     def action_move_create(self):
#         """ Creates invoice related analytics and financial move lines """
#         res = super(AccountInvoice, self).action_move_create()
#         for inv in self:
#             if inv.period_id and inv.move_id:
#                 inv.move_id.period_id = inv.period_id
#         return res

# ~ class AccountMove(models.Model):
    # ~ _inherit = 'account.move'

    # ~ payment_period_id = fields.Many2one(store=True,comodel_name='account.period', string='The period for the account payment', compute="_get_period_from_payment", readonly=True)
    # ~ payment_date = fields.Date(store=True, string='The date for the account payment', compute="_get_date_from_payment", readonly=True)

    # ~ api.depends("payment_id.period")
    # ~ def _get_period_from_payment(self):
        # ~ for rec in self:
            # ~ rec.payment_period_id = rec.payment_id.period_id

    # ~ api.depends("payment_id.date")
    # ~ def _get_period_from_payment(self):
        # ~ for rec in self:
            # ~ rec.payment_date = rec.payment_id.date
