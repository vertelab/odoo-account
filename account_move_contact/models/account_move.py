from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    contact_id = fields.Many2one('res.partner', string='Contact')
