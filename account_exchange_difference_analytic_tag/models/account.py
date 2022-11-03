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

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    def reconcile(self):
        res = super(AccountMoveLine, self).reconcile()
        _logger.warning(f"{res=}")
        if res and 'full_reconcile' in res and res['full_reconcile'].exchange_move_id:
          account_move = res['full_reconcile'].exchange_move_id
          account_expense = self.env.company.expense_currency_exchange_account_id
          account_income = self.env.company.income_currency_exchange_account_id
          account_full_reconcile_record = self.env['account.full.reconcile'].search([('exchange_move_id','=', res['full_reconcile'].exchange_move_id.id)])
          account_full_reconcile_record_moves = account_full_reconcile_record.reconciled_line_ids.move_id
          lines = account_full_reconcile_record_moves.line_ids
            
          project_no = False
          area_of_responsibility = False
          for line in lines:
                if line.project_no:
                    project_no = line.project_no
                if line.area_of_responsibility:
                    area_of_responsibility = line.area_of_responsibility
          
          account_full_reconcile_record = self.env['account.full.reconcile'].search([('exchange_move_id','=', res['full_reconcile'].exchange_move_id.id)])
          account_full_reconcile_record_moves = account_full_reconcile_record.reconciled_line_ids.move_id
          tags = lines.analytic_tag_ids
          # ~ _logger.warning(f"{tags=}")
          for line in res['full_reconcile'].exchange_move_id.line_ids:
            if line.account_id == account_expense or line.account_id == account_income:
                line.project_no = project_no
                line.area_of_responsibility= area_of_responsibility
                line.write({'analytic_tag_ids':tags})
            if int(line.account_id.code) >= 3000 and  int(line.account_id.code) <= 9999:
                line.project_no = project_no
                line.area_of_responsibility = area_of_responsibility
                line.write({'analytic_tag_ids':tags})
                
          return res
        
      
