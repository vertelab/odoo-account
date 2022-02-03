# -*- coding: utf-8 -*-
#from . import res_partner

# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_compare, date_utils, email_split, email_re
from odoo.tools.misc import formatLang, format_date, get_lang

from datetime import date, timedelta
from collections import defaultdict
from itertools import zip_longest
from hashlib import sha256
from json import dumps

import ast
import json
import re
import warnings
import logging
_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    # ~ @api.depends('analytic_account_id','analytic_account_id.group_id','analytic_account_id.group_id.name')
    # ~ def set_analytic_group_use_in_filter(self):
        # ~ _logger.warning(f"{self}")
        # ~ _logger.warning("record !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        # ~ _logger.warning("record !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        # ~ _logger.warning("record !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        # ~ for record in self:
            # ~ _logger.warning("record !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            # ~ _logger.warning(f"analytic_account_id={record.analytic_account_id}")
            # ~ _logger.warning(f"analytic_account_id.group_id={record.analytic_account_id.group_id}")
            # ~ _logger.warning(f"analytic_account_id.group_id.name={record.analytic_account_id.group_id.name}")
            # ~ _logger.warning("record !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            # ~ record._compute_analytic_group_use_in_filter_default()
    
    @api.model
    def create(self, values):
        res = super(AccountMoveLine, self).create(values)
        for record in self:
            if record.analytic_account_id and record.analytic_account_id.group_id:
                record.analytic_group_use_in_filter = record.analytic_account_id.group_id.name
        # here you can do accordingly
        return res

    @api.depends("analytic_account_id","analytic_account_id.group_id","analytic_account_id.group_id.name")
    def set_analytic_group_use_in_filter_depends(self):
        for record in self:
            if record.analytic_account_id and record.analytic_account_id.group_id:
                record.analytic_group_use_in_filter = record.analytic_account_id.group_id.name
    
    
    
    def _set_on_analytic_group_use_in_filter_all_record(self):
        records = self.env['account.move.line'].search([])
        records.set_analytic_group_use_in_filter()
        
    
    # ~ @api.model
    def set_analytic_group_use_in_filter(self):
        for record in self:
            _logger.warning(f"{record}")
            _logger.warning("record !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! _set_analytic_group_use_in_filter_default")
            if record.analytic_account_id and record.analytic_account_id.group_id:
                record.analytic_group_use_in_filter = record.analytic_account_id.group_id.name
            else:
                record.analytic_group_use_in_filter = False

    analytic_group_use_in_filter = fields.Char()
    # ~ new_field = fields.Char(compute=_compute_analytic_group_use_in_filter_default)
    
    
    
    
class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    def write(self, values):
        res = super(AccountAnalyticAccount, self).write(values)
        for record in self:
            move_line_records = self.env['account.move.line'].search([('analytic_account_id','=',record.id)])
            move_line_records.set_analytic_group_use_in_filter()
        # here you can do accordingly
        return res
        
    def name_get(self):
        res = []
        for analytic in self:
            name = analytic.name
            if analytic.code:
                name =  name + ' [' + analytic.code + '] ' 
            if analytic.partner_id.commercial_partner_id.name:
                name = name + ' - ' + analytic.partner_id.commercial_partner_id.name
            res.append((analytic.id, name))
        return res
    
    
    
    
class AccountAnalyticGroup(models.Model):
    _inherit = "account.analytic.group"

    def write(self, values):
        _logger.warning("account.analytic.group write !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        res = super(AccountAnalyticGroup, self).write(values)
        for record in self:
            analytic_account_ids = self.env['account.analytic.account'].search([('group_id','=',record.id)])
            for analytic_account_id in analytic_account_ids:
                move_line_records = self.env['account.move.line'].search([('analytic_account_id','=',analytic_account_id.id)])
                move_line_records.set_analytic_group_use_in_filter()
        # here you can do accordingly
        return res
