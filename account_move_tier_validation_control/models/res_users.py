# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    company_currency_id = fields.Many2one(string='Company Currency', readonly=True, related='company_id.currency_id')
    allowed_to_validate = fields.Boolean(string='Allowed To Approve')
    max_validation_amount = fields.Monetary(string='Max Approve Amount', currency_field='company_currency_id')
    allowed_to_review = fields.Boolean(string='Allowed To Review')
