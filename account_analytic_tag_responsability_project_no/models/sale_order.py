from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        if len(self.order_line.filtered(lambda line: not line.area_of_responsibility and not line.display_type)) > 0:
            raise ValidationError(_("Kindly select a Cost Center tag for all line items"))
        res = super(SaleOrder, self).action_confirm()
        return res
