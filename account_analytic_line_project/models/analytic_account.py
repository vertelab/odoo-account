# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from collections import defaultdict
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    project_id = fields.Many2one("project.project",
                                 string="Related project",
                                 )


class Project(models.Model):
    _inherit = "project.project"

    analytic_line_ids = fields.One2many("account.analytic.line",
                                        "project_id",
                                        string="Related analytic lines",
                                        )

