# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import SQL, Query, unique
from odoo.tools.float_utils import float_compare, float_round


class AnalyticMixin(models.AbstractModel):
    _inherit = 'analytic.mixin'

