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
from odoo.exceptions import UserError, ValidationError, Warning

import logging

_logger = logging.getLogger(__name__)

FIELDS = ['move_type','name','partner_id','invoice_date','journal_id','invoice_line_ids','line_ids','company_id','state']


class AccountAccount(models.Model):
    _inherit = 'account.account'

    def get_debit_credit_balance(self, period, target_move):
        self.ensure_one()
        if not target_move or target_move == 'all':
            target_move = ['draft', 'posted']
        else:
            target_move = [target_move]
        lines = self.env['account.move.line'].search(
            [('move_id.period_id', '=', period.id), ('account_id', '=', self.id),
             ('move_id.state', 'in', target_move)])  # move lines with period_id
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
        _period_ids = self.env['account.period'].get_period_ids(
            self._context.get('period_start'), self._context.get('period_stop', self._context.get('period_start'))
        )
        if self._context.get('accounting_method') == "cash":
             domain = [('move_id.payment_period_id', 'in', _period_ids), ('account_id', '=', self.id)]
            
        else:
            domain = [('move_id.period_id', 'in', _period_ids), ('account_id', '=', self.id)]

        if self._context.get('target_move') in ['draft', 'posted']:
            domain.append(('move_id.state', '=', self._context.get('target_move')))
        return sum([a.balance for a in self.env['account.move.line'].search(domain)])

    
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
