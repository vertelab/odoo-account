# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    move_tier_validator = fields.Many2one('res.users', tracking=True,string='Move Validator') ### attesterare
    move_tier_validators = fields.Many2many('res.users', tracking=True,string='Move Validators') ### attesterare
    
# ~ class AccountMove(models.Model):
    # ~ _inherit = "res.users"
    # ~ validation_needed_invoice_id = fields.Many2one('account.move',string='Move Validator') ### attesterare
    
    def _get_under_validation_exceptions(self):
        res = super(AccountMove, self)._get_under_validation_exceptions()
        res.append("exclude_payment")
        res.append("exclude_payment_partner")
        res.append("exclude_payment_partner_and_move")
        return res