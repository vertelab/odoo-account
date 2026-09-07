# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def generated2uploaded(self):
        """Override to skip post_and_reconcile for pending payment methods.

        When the payment method has `pending_until_reconciliation = True`,
        the payment order transitions to "uploaded" state WITHOUT posting
        the payments or reconciling them against invoices. This keeps
        invoices in "in_payment" (pågående) state until bank statement
        reconciliation.

        For manual/standard payment methods (pending_until_reconciliation = False),
        the original behavior is preserved: payments are posted and reconciled.
        """
        self.ensure_one()

        if self.payment_method_id.pending_until_reconciliation:
            # Pending mode: transition to uploaded WITHOUT post_and_reconcile
            _logger.info(
                "Payment order %s (method: %s): pending_until_reconciliation=True, "
                "skipping post_and_reconcile. Invoices remain in_payment.",
                self.name,
                self.payment_method_id.code,
            )
            self.write(
                {
                    "state": "uploaded",
                    "date_uploaded": fields.Date.context_today(self),
                }
            )
            # Recompute payment_state on the invoices so they are flagged
            # 'in_payment' even though no payment/reconciliation was created.
            moves = self.payment_line_ids.move_line_id.move_id
            if moves:
                moves._compute_payment_state()
            return True
        else:
            # Standard mode: keep existing behavior
            return super().generated2uploaded()
