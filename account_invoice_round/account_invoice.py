# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2018 Vertel AB (<http://vertel.se>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import api, models, fields, _
import logging
_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    @api.one
    def account_invoice_round(self):
        account = self.env['account.account'].search([('code','=','3740')],limit=1) 
        if self.state == 'draft':
            if round(self.amount_total,0) !=  self.amount_total:
                self.env['account.invoice.line'].search([('invoice_id','=',self.id),('is_rounded','=',True)]).unlink()
                amount_untaxed = sum(line.price_subtotal for line in self.invoice_line)
                amount_tax = sum(line.amount for line in self.tax_line)
                amount_total = self.amount_untaxed + self.amount_tax
                
                self.env['account.invoice.line'].create({
                    'invoice_id': self.id,
                    'account_id': account.id,
                    'quantity': 1.0,
                    'price_unit': round(amount_total,0) - amount_total,
                })
    
    @api.multi
    def button_compute(self, set_total=False):
        for invoice in self:
            invoice.account_invoice_round()
        return super(AccountInvoice,self).button_compute()

class AccountInvoice(models.Model):
    _inherit = 'account.invoice.line'
    
    is_rounded = fields.Boolean(string='Rounded', help='This line is for rounding purpuses')
    
