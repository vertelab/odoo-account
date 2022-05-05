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

    def get_group_id_default(self):
        return self.account_id and self.account_id.group_id

    @api.depends("account_id", "account_id.group_id")
    def get_group_id(self):
        for record in self:
            self.group_id = self.account_id.group_id


    group_id = fields.Many2one("account.analytic.group",
                               string="Related group",
                               default=get_group_id_default,
                               compute="get_group_id",
                               store=True,
                               )


class Project(models.Model):
    _inherit = "project.project"

    analytic_line_ids = fields.One2many("account.analytic.line",
                                        "project_id",
                                        string="Related analytic lines",
                                        )

