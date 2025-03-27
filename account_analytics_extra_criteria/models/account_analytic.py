# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAnalyticDistributionModel(models.Model):
    _inherit = "account.analytic.distribution.model"

    hr_department_id = fields.Many2one('hr.department', string="Department")

    def _get_default_search_domain_vals(self):
        res = super()._get_default_search_domain_vals() | {
            'hr_department_id': False,
        }
        return res

    def _create_domaindep(self, fname, value):
        if fname == 'hr_department_id':
            return [(fname, 'in', [value, False])]
        return super()._create_domain(fname, value)

