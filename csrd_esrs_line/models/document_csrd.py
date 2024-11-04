from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)

class DocumentCSRD(models.Model):
    _description = ''
    _inherit = 'document.csrd'

    uom_id = fields.Many2one(comodel_name="uom.uom")
    implement_volume


