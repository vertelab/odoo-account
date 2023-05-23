from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super()._create_invoices(grouped, final, date)

        # Goes through all the created Invoices (account.moves), and finds
        # the customer in the originating sale order(s), and puts said
        # customer in the contact field in the account.move
        for move in moves:
            if move.invoice_origin:
                order_name = move.invoice_origin.split(',')[0]
                for order in self:
                    if order.name == order_name:
                        move.contact_id = order.partner_id.id
                        break
                        
        return moves
