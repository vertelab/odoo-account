# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = "res.users"
    allowed_to_validate = fields.Boolean(string='Allowed To Validate')
    max_validation_amount = fields.Monetary(string='Max Validation Amount')
    
