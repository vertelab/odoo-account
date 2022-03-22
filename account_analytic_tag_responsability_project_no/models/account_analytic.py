# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAnalyticDefault(models.Model):
    _inherit = "account.analytic.tag"

    type_of_tag = fields.Selection([('area_of_responsibility', 'Area of Responsibility'),('project_number', 'Project Number'),('no_type', 'No Type'),],'Tag Type', default='no_type')
