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
import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    amount_rounded = fields.Float(string='Rounded', digits=dp.get_precision('Account'),store=True, readonly=True, compute='_compute_amount')
    do_round = fields.Boolean(string='Do rounding',default=True)
        
    # ~ @api.multi
    # ~ def button_reset_taxes(self):
        # ~ account_invoice_tax = self.env['account.invoice.tax']
        # ~ ctx = dict(self._context)
        # ~ for invoice in self:
            # ~ self._cr.execute("DELETE FROM account_invoice_tax WHERE invoice_id=%s AND manual is False", (invoice.id,))
            # ~ self.invalidate_cache()
            # ~ partner = invoice.partner_id
            # ~ if partner.lang:
                # ~ ctx['lang'] = partner.lang
            # ~ for taxe in account_invoice_tax.compute(invoice.with_context(ctx)).values():
                # ~ account_invoice_tax.create(taxe)
        # ~ # dummy write on self to trigger recomputations
        # ~ return self.with_context(ctx).write({'invoice_line': []})
        
    @api.one
    @api.depends('invoice_line.price_subtotal', 'tax_line.amount','do_round')
    def _compute_amount(self):
        super(account_invoice,self)._compute_amount()
        if self.type == 'out_invoice' and self.do_round:
            self.amount_rounded = round((self.amount_untaxed + self.amount_tax),0) - (self.amount_untaxed + self.amount_tax)
            self.amount_total = self.amount_rounded + self.amount_untaxed + self.amount_tax
                
    
    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        """ finalize_invoice_move_lines(move_lines) -> move_lines

            Hook method to be overridden in additional modules to verify and
            possibly alter the move lines to be created by an invoice, for
            special cases.
            :param move_lines: list of dictionaries with the account.move.lines (as for create())
            :return: the (possibly updated) final move_lines to create for this invoice
        """
        move_lines = super(account_invoice,self).finalize_invoice_move_lines(move_lines)
        if self.do_round and self.amount_rounded:
            account_round = self.env['account.account'].search([('code','=',self.env['ir.config_parameter'].get_param('account_invoice_round.account_round','3740'))],limit=1)
            if not account_round:
                raise Warning(_('Account for rounding missing'))
            line_receivable = [d for (x,x,d) in move_lines if d.get('account_id') in self.env['account.account'].search([('type','=','receivable')]).mapped('id')]
            if line_receivable and len(line_receivable)>0:
                line_receivable[0]['debit'] += self.amount_rounded

            move_lines.append((0, 0, {
                    'analytic_account_id': False, 
                    'tax_code_id': False, 
                    'analytic_lines': [], 
                    'tax_amount': 0.0, 
                    'name': _('Rounded amount'), 
                    'ref': False, 
                    'currency_id': False, 
                    'product_id': False, 
                    'date_maturity': False, 
                    'credit': self.amount_rounded if self.amount_rounded > 0.0 else  False, 
                    'debit': self.amount_rounded * -1.0 if self.amount_rounded < 0.0 else  False, 
                    'date': fields.Date.today(), 
                    'amount_currency': 0, 
                    'product_uom_id': False, 
                    'quantity': 1.0, 
                    'partner_id': False, 
                    'account_id': account_round.id}))
        # ~ _logger.warn('Move Lines %s' % [(d['account_id'],d['credit'],d['debit']) for x,x,d in move_lines])
        return move_lines

class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    rounding_account_id = fields.Many2one(comodel_name='account.account',
                            string='Rounding account',domain=[('type', '=', 'other')])

    @api.one
    def set_account_round(self):
        self.env['ir.config_parameter'].set_param('account_invoice_round.account_round',(self.rounding_account_id.code if self.rounding_account_id else '3740'), groups=['base.group_system'])

    @api.model
    def get_default_account_round(self,fields):
        account_round = self.env['account.account'].search([('code','=',self.env['ir.config_parameter'].get_param('account_invoice_round.account_round','3740'))],limit=1)
        # ~ raise Warning(account_rou)
        # ~ return {'rounding_account_id': 123}
        return {
            'rounding_account_id': account_round.id if account_round else None,
        }

