# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountMove(models.Model):
    """Ensure invoices on a 'pending until reconciliation' payment order
    get payment_state = 'in_payment' (pågående) as soon as the order is
    generated/uploaded, even though no payment/reconciliation is created.

    The standard _compute_payment_state only returns 'in_payment' when the
    move has a partial reconcile or a matched payment. Because
    account_payment_order_pending skips post_and_reconcile(), invoices on a
    pending payment order would otherwise stay 'not_paid' despite being
    queued for payment on the bank. This override corrects that.
    """

    _inherit = "account.move"

    def _compute_payment_state(self):
        """Run standard computation, then force 'in_payment' on moves that
        are on a pending-until-reconciliation payment order."""
        res = super()._compute_payment_state()

        # Moves whose payment lines belong to an order whose payment method
        # has pending_until_reconciliation=True and that has been generated
        # or uploaded (i.e. the payment file was handed to the bank but the
        # bank has not yet confirmed/reconciled the individual payments).
        pending_move_ids = (
            self.env["account.payment.line"]
            .sudo()
            .search(
                [
                    ("order_id.state", "in", ("generated", "uploaded")),
                    ("order_id.payment_method_id.pending_until_reconciliation", "=", True),
                ]
            )
            .move_line_id.move_id
        )

        if pending_move_ids:
            moves = self.filtered(
                lambda m: m.id in pending_move_ids.ids
                and m.payment_state != "in_payment"
            )
            if moves:
                moves.payment_state = "in_payment"

        return res
