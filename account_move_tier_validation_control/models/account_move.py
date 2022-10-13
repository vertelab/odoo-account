# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

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
