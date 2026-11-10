import logging
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


from odoo.tools import float_compare

_logger = logging.getLogger(__name__)



class ProductCategory(models.Model):
    _inherit = "product.category"

    project_no = fields.Many2one(comodel_name='account.analytic.tag', string='Project', readonly=False,
                                 domain="[('type_of_tag', '=', 'project_number')]")
    area_of_responsibility = fields.Many2one(comodel_name='account.analytic.tag', string='Cost Center',
                                             readonly=False, domain="[('type_of_tag', '=', 'area_of_responsibility')]")
