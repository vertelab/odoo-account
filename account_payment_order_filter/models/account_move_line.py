# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2017 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import api, fields, models, _, exceptions
from odoo.osv import expression
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import Warning

import logging
_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    # ~ Overwritten to make sure the communication value gets filled by something atleast 
    def _prepare_payment_line_vals(self, payment_order):
        self.ensure_one()
        assert payment_order, "Missing payment order"
        aplo = self.env["account.payment.line"]
        # default values for communication_type and communication
        communication_type = "normal"
        communication = self.ref or self.name
        # change these default values if move line is linked to an invoice
        if self.move_id.is_invoice():
            if self.move_id.reference_type != "none":
                communication = self.move_id.ref
                ref2comm_type = aplo.invoice_reference_type2communication_type()
                communication_type = ref2comm_type[self.move_id.reference_type]
            else:
                if (
                    self.move_id.move_type in ("in_invoice", "in_refund")
                    and self.move_id.ref
                ):
                    communication = self.move_id.ref
                elif "out" in self.move_id.move_type:
                    # Force to only put invoice number here
                    communication = self.move_id.name
                else:#additions
                        communication = self.move_id.name
        if self.currency_id:
            currency_id = self.currency_id.id
            amount_currency = self.amount_residual_currency
        else:
            currency_id = self.company_id.currency_id.id
            amount_currency = self.amount_residual
            # TODO : check that self.amount_residual_currency is 0
            # in this case
        if payment_order.payment_type == "outbound":
            amount_currency *= -1
        # ~ partner_bank_id = self.partner_bank_id.id or first(self.partner_id.bank_ids).id
        partner_bank_id = self.partner_bank_id.id
        vals = {
            "order_id": payment_order.id,
            "partner_bank_id": partner_bank_id,
            "partner_id": self.partner_id.id,
            "move_line_id": self.id,
            "communication": communication,
            "communication_type": communication_type,
            "currency_id": currency_id,
            "amount_currency": amount_currency,
            "date": False,
            # date is set when the user confirms the payment order
        }
        _logger.warning(f"jakmar vals {vals}")
        return vals
