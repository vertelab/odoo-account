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
from odoo.exceptions import Warning

import logging
_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    default_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, copy=False, ondelete='restrict',
        string='Default Account',
        domain = "[]"
       )
    payment_debit_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, copy=False, ondelete='restrict',
        help="Incoming payments entries triggered by invoices/refunds will be posted on the Outstanding Receipts Account "
             "and displayed as blue lines in the bank reconciliation widget. During the reconciliation process, concerned "
             "transactions will be reconciled with entries on the Outstanding Receipts Account instead of the "
             "receivable account.", string='Outstanding Receipts Account',
             domain = "[]"
        )
    payment_credit_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, copy=False, ondelete='restrict',
        help="Outgoing payments entries triggered by bills/credit notes will be posted on the Outstanding Payments Account "
             "and displayed as blue lines in the bank reconciliation widget. During the reconciliation process, concerned "
             "transactions will be reconciled with entries on the Outstanding Payments Account instead of the "
             "payable account.", string='Outstanding Payments Account',
             domain = "[]"
        )
    suspense_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, ondelete='restrict', readonly=False, store=True,
        compute='_compute_suspense_account_id',
        help="Bank statements transactions will be posted on the suspense account until the final reconciliation "
             "allowing finding the right account.", string='Suspense Account',
        domain = "[]"
       )
        
    @api.constrains('type', 'default_account_id')
    def _check_type_default_account_id_type(self):
        for journal in self:
            if journal.type in ('sale', 'purchase') and journal.default_account_id.user_type_id.type in ('receivable', 'payable'):
                _logger.warning(_("The type of the journal's default credit/debit account shouldn't be 'receivable' or 'payable'."))

