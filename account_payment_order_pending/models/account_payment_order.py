# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def generated2uploaded(self):
        """Override to post payments but skip reconciliation for pending methods.

        When the payment method has `pending_until_reconciliation = True`, the
        payment order transitions to "uploaded" state WITH the payments posted
        (state 'in_process') but WITHOUT reconciling them against the invoices.
        This keeps the invoices in "in_payment" (pågående) until bank statement
        reconciliation, while the payments themselves read 'in_process' — both
        records are marked 'paid' only once reconciled with a bank transaction.

        For manual/standard payment methods (pending_until_reconciliation = False),
        the original behavior is preserved: payments are posted and reconciled.
        """
        self.ensure_one()

        if self.payment_method_id.pending_until_reconciliation:
            # Pending mode: post the payments (in_process) but skip the
            # reconciliation so invoices remain in_payment.
            _logger.info(
                "Payment order %s (method: %s): pending_until_reconciliation=True, "
                "posting payments but skipping reconciliation. Invoices remain in_payment.",
                self.name,
                self.payment_method_id.code,
            )
            self.payment_ids.action_post()
            # A payment from an asset_cash account would be auto-set to 'paid'
            # by action_post(); for a pending-until-reconciliation order it must
            # stay 'in_process' until the bank statement reconcile.
            self.payment_ids.filtered(lambda p: p.state == 'paid').state = 'in_process'
            self.write(
                {
                    "state": "uploaded",
                    "date_uploaded": fields.Date.context_today(self),
                }
            )
            # Recompute payment_state on the invoices so they are flagged
            # 'in_payment' even though no reconciliation was created.
            moves = self.payment_line_ids.move_line_id.move_id
            if moves:
                moves._compute_payment_state()
            return True
        else:
            # Standard mode: keep existing behavior
            return super().generated2uploaded()
