# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends('amount_total_signed')
    def _compute_amount_total_signed_absolute(self):
        context_copy = self.env.context.copy()
        context_copy.update({'check_move_period_validity': False})
        for move in self:
            move.with_context(context_copy).amount_total_signed_absolute = abs(move.amount_total_signed)

    amount_total_signed_absolute = fields.Monetary(string='Absolute Value of Signed Total', store=True, readonly=True,
                                                   compute='_compute_amount_total_signed_absolute')

    def _get_under_validation_exceptions(self):
        res = super(AccountMove, self)._get_under_validation_exceptions()
        res.append("amount_total_signed_absolute")
        return res
        
    @api.model
    def create(self, vals):
        res = super().create(vals)
        for record in res:
            if record.move_tier_validator.max_validation_amount < record.amount_total_signed_absolute:
                raise UserError(f"{record.move_tier_validator.name} is not qualified to handle invoices above {record.move_tier_validator.max_validation_amount} {record.move_tier_validator.company_currency_id}.")
        return res

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if record.move_tier_validator.max_validation_amount < record.amount_total_signed_absolute:
                raise UserError(f"{record.move_tier_validator.name} is not qualified to handle invoices above {record.move_tier_validator.max_validation_amount} {record.move_tier_validator.company_currency_id}.")
        return res
