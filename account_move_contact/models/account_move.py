from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_order_id = fields.Many2one('sale.order', string='Related Sale Order')
    contact_id = fields.Many2one(related='sale_order_id.partner_id', string='Contact', readonly=True)
