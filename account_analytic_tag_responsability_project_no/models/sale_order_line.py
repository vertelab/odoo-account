from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    project_no = fields.Many2one(comodel_name='account.analytic.tag', string='Project Analytic Tag', readonly=False,
                                 domain="[('type_of_tag', '=', 'project_number')]")
    area_of_responsibility = fields.Many2one(comodel_name='account.analytic.tag', string='Place Analytic Tag',
                                             readonly=False, domain="[('type_of_tag', '=', 'area_of_responsibility')]")


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    project_no = fields.Many2one(comodel_name='account.analytic.tag', string='Project Analytic Tag', readonly=False,
                                 domain="[('type_of_tag', '=', 'project_number')]")
    area_of_responsibility = fields.Many2one(comodel_name='account.analytic.tag', string='Place Analytic Tag',
                                             readonly=False, domain="[('type_of_tag', '=', 'area_of_responsibility')]")
