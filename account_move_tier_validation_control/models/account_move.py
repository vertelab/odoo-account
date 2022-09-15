# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    # ~ move_tier_validator = fields.Many2one('res.users', tracking=True,string='Move Validator', domain=lambda self: [("groups_id", "=", self.env.ref("account_move_tier_validation_group.group_validator").id)]) ### attesterare
    # ~ move_tier_validators = fields.Many2many('res.users', tracking=True,string='Move Validators', domain=lambda self: [("groups_id", "=", self.env.ref("account_move_tier_validation_group.group_validator").id)]) ### attesterare

    @api.depends('amount_total_signed')
    def _compute_amount_total_signed_absolute(self):
        context_copy = self.env.context.copy()
        context_copy.update({'check_move_period_validity': False})
        for move in self:
            move.with_context(context_copy).write({'amount_total_signed_absolute': abs(move.amount_total_signed)})

    amount_total_signed_absolute = fields.Monetary(string='Absolute Value of Signed Total', store=True, readonly=True,
                                                   compute='_compute_amount_total_signed_absolute')

    def _get_under_validation_exceptions(self):
        res = super(AccountMove, self)._get_under_validation_exceptions()
        res.append("amount_total_signed_absolute")
        return res
