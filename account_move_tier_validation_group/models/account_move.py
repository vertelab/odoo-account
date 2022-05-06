# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    move_tier_validator = fields.Many2one('res.users', tracking=True,string='Move Validator', domain=lambda self: [("groups_id", "=", self.env.ref("account_move_tier_validation_group.group_validator").id)]) ### attesterare
    move_tier_validators = fields.Many2many('res.users', tracking=True,string='Move Validators', domain=lambda self: [("groups_id", "=", self.env.ref("account_move_tier_validation_group.group_validator").id)]) ### attesterare
    

    
