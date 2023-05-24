from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"
    _description = "Sales Advance Payment Invoice Contact"

    def _prepare_invoice_values(self, order, name, amount, so_line):
        vals = super()._prepare_invoice_values(order, name, amount, so_line)
        vals['sale_order_id'] = order.id
        return vals
