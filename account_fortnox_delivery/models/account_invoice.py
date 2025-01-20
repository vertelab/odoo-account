# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
import logging
import json
import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)



class AccountInvoice(models.Model):
    _inherit = "account.move"

    def fortnox_invoice_vals(self, invoice, invoice_lines):
        invoice_vals = super(AccountInvoice, self).fortnox_invoice_vals(invoice, invoice_lines)
        
        source_orders = invoice.line_ids.sale_line_ids.order_id
        #raise Exception(f"{source_orders=}")
        if source_orders:
            carrier_id = source_orders[0].carrier_id
            if carrier_id and carrier_id.fortnox_code:
                invoice_vals["WayOfDelivery"] = carrier_id.fortnox_code
            elif carrier_id and not carrier_id.fortnox_code:
                raise UserError(f"""
The carrier ({carrier_id.name}) is missing an fortnox code.
Please add it.
""")
            
            confirmed_pickings = source_orders.mapped('picking_ids').filtered(
                lambda p: p.state == 'confirmed'
            )
            latest_picking_date = False
            if confirmed_pickings:
                latest_picking_date = confirmed_pickings.sorted(
                    key=lambda p: p.date_done, reverse=True
                )[0].date_done
            else:
                not_canceled_pickings = source_orders.mapped('picking_ids').filtered(
                    lambda p: p.state != 'cancel'
                )
                if not_canceled_pickings:
                    latest_picking_date = not_canceled_pickings.sorted(
                        key=lambda p: p.scheduled_date, reverse=True
                    )[0].scheduled_date
            if latest_picking_date:
               invoice_vals["DeliveryDate"] = str(latest_picking_date.date())
        _logger.warning(f"{invoice_vals=}")
        return invoice_vals


