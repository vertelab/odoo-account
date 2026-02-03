import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class Users(models.Model):
    _inherit = "res.users"

    project_no = fields.Many2one(
        comodel_name='account.analytic.tag', string='Project', readonly=False,
        domain="[('type_of_tag', '=', 'project_number')]"
    )
    area_of_responsibility = fields.Many2one(
        comodel_name='account.analytic.tag', string='Cost Center',
        readonly=False, domain="[('type_of_tag', '=', 'area_of_responsibility')]"
    )