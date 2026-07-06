# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    # Override generated2uploaded for autogiro-specific behavior
    def generated2uploaded(self):
        """For autogiro payment orders, skip post_and_reconcile entirely.
        
        The autogiro payment method already has pending_until_reconciliation=True
        (set via account_payment_order_pending), so the super call handles this.
        We add autogiro-specific logging here.
        """
        result = super().generated2uploaded()
        if self.payment_method_id.code == "autogiro":
            _logger.info(
                "Autogiro payment order %s: uploaded without posting. "
                "Supplier invoices remain in_payment until bank reconciliation.",
                self.name,
            )
        return result
