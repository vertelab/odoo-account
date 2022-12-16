from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        if len(self.order_line.filtered(lambda line: not line.area_of_responsibility and not line.display_type)) > 0:
            raise ValidationError(_("Kindly select a Cost Center tag for all line items"))
        res = super(PurchaseOrder, self).button_confirm()
        return res
        
    def action_create_invoice(self):
        _logger.warning("create_invoices"*100)
        vals = super().action_create_invoice()
        
        for order in self:
            for invoice in order.invoice_ids:
                for line in invoice.line_ids:
                    if line.purchase_line_id:
                            line.project_no = line.purchase_line_id.project_no
                            line.area_of_responsibility = line.purchase_line_id.area_of_responsibility
        
        return vals
