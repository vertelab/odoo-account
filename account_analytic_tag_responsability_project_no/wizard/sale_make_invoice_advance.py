# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def create_invoices(self):
        vals = super().create_invoices()
        
        for sale_order in self.env['sale.order'].browse(self._context.get('active_ids', [])):
            for invoice in sale_order.invoice_ids:
                for line in invoice.line_ids:
                    if line.sale_line_ids:
                        for sale_line in line.sale_line_ids:
                            if sale_line.project_no:
                                line.project_no = sale_line.project_no
                            if sale_line.area_of_responsibility:
                                line.area_of_responsibility = sale_line.area_of_responsibility
        return vals
        
        
  
