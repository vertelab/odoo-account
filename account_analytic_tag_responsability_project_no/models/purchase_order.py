from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        if len(self.order_line.filtered(lambda line: not line.area_of_responsibility)) > 0:
            raise ValidationError(_("Kindly select area of responsibility tag for all line items"))
        res = super(PurchaseOrder, self).button_confirm()
        return res
