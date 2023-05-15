from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = self.env['account.move']
        for record in self:
            move = super(SaleOrder, record)._create_invoices(grouped, final, date)
            move.sale_order_id = record.id
            if move:
                moves += move
        return moves
        #if len(moves) > 0:
        #    return moves
        #else:
        #    return False
