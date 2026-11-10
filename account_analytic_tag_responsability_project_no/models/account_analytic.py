# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAnalyticTag(models.Model):
    _inherit = "account.analytic.tag"

    type_of_tag = fields.Selection(
        [('area_of_responsibility', 'Cost Center'), ('project_number', 'Project'),
         ('no_type', 'No Type'), ], 'Tag Type', default='no_type')

    # ~ def write(self, values):
    # ~ res = super(AccountAnalyticTag, self).write(values)
    # ~ for record in self:
    # ~ move_line_records = self.env['account.move.line'].search([('analytic_tag_ids','in',record.id)])
    # ~ move_line_records._depends_analytic_tag_ids()
    # ~ sale_order_line_records = self.env['sale.order.line'].search([('analytic_tag_ids','in',record.id)])
    # ~ sale_order_line_records._depends_analytic_tag_ids()
    # ~ purchase_order_line_records = self.env['purchase.order.line'].search([('analytic_tag_ids','in',record.id)])
    # ~ purchase_order_line_records._depends_analytic_tag_ids()
    # ~ return res
