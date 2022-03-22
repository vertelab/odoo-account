# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends('tax_repartition_line_id.invoice_tax_id', 'tax_repartition_line_id.refund_tax_id') #Otherwise the tax lines wont have analytic accounts applied on itself
    def _compute_tax_line_id(self):
            res = super(AccountMoveLine, self)._compute_tax_line_id()
            self._compute_analytic_account_id()
            return res
            
    # ~ @api.depends('product_id', 'account_id', 'partner_id', 'date')
    def _compute_analytic_account_id_background_lines(self):
        for record in self:
                rec = self.env['account.analytic.default'].account_get(
                    product_id=record.product_id.id,
                    partner_id=record.partner_id.commercial_partner_id.id or record.move_id.partner_id.commercial_partner_id.id,
                    account_id=record.account_id.id,
                    user_id=record.env.uid,
                    date=record.date,
                    company_id=record.move_id.company_id.id
                )
                if rec:
                    record.analytic_account_id = rec.analytic_id

    
    @api.depends('product_id', 'account_id', 'partner_id', 'date')
    def _compute_analytic_account_id(self):
        _logger.warning("_compute_analytic_account")
        _logger.warning("_compute_analytic_account")
        for record in self:
                rec = self.env['account.analytic.default'].account_get(
                    product_id=record.product_id.id,
                    partner_id=record.partner_id.commercial_partner_id.id or record.move_id.partner_id.commercial_partner_id.id,
                    account_id=record.account_id.id,
                    user_id=record.env.uid,
                    date=record.date,
                    company_id=record.move_id.company_id.id
                )
                _logger.warning(f"analytictest{record=}")
                _logger.warning(f"analytictest{rec=}")
                if rec:
                    record.analytic_account_id = rec.analytic_id
                    union_record_ids=rec.analytic_tag_ids | record.analytic_tag_ids
                    record.analytic_tag_ids = union_record_ids
                    

