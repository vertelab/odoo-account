# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _prepare_fortnox_invoice_vals(self, invoice_lines):
        """Add the delivery method and the delivery date to the Fortnox payload.

        Odoo 18 renamed the hook: the 16.0 module overrode
        ``fortnox_invoice_vals(self, invoice, invoice_lines)``, the 18.0
        ``account_fortnox`` has ``_prepare_fortnox_invoice_vals(self, invoice_lines)``
        and reads the invoice from ``self``.
        """
        invoice_vals = super()._prepare_fortnox_invoice_vals(invoice_lines)

        source_orders = self.line_ids.sale_line_ids.order_id
        if not source_orders:
            return invoice_vals

        carrier = source_orders[0].carrier_id
        if carrier:
            if not carrier.fortnox_code:
                raise UserError(_(
                    "The carrier (%s) is missing a Fortnox code. Please add it.",
                    carrier.name,
                ))
            invoice_vals["WayOfDelivery"] = carrier.fortnox_code

        pickings = source_orders.mapped("picking_ids")
        done = pickings.filtered(lambda p: p.state == "done" and p.date_done)
        if done:
            latest = done.sorted(key=lambda p: p.date_done, reverse=True)[0]
            invoice_vals["DeliveryDate"] = str(latest.date_done.date())
        else:
            open_pickings = pickings.filtered(lambda p: p.state != "cancel")
            if open_pickings:
                latest = open_pickings.sorted(
                    key=lambda p: p.scheduled_date or p.create_date, reverse=True
                )[0]
                if latest.scheduled_date:
                    invoice_vals["DeliveryDate"] = str(latest.scheduled_date.date())

        return invoice_vals
