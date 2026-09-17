# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountMove(models.Model):
    """Show a bill as 'in_payment' (pågående) from the moment it is linked to
    a payment or a payment order, until the bank transaction is reconciled.

    Odoo's standard computation only yields 'in_payment' when the move carries
    a real partial reconcile or a matched payment. A bill that is merely queued
    for payment — on a payment order, or on a payment that has not reached the
    bank yet — has none of those, so it would read 'not_paid' even though the
    money is on its way.

    This override derives the pending state from the links that already exist
    (payment lines and matched payments). No extra flag is stored, so there is
    nothing to keep in sync:

    * linked to a payment order  -> account.payment.line exists
    * linked to a payment        -> account.move.matched_payment_ids

    Once the bank transaction is reconciled, the standard computation becomes
    authoritative again: the move is settled (amount_residual == 0) and is left
    alone. The settlement itself is performed by
    AccountPartialReconcile._settle_pending_payment_orders().
    """

    _inherit = "account.move"

    def _is_pending_bank_settlement(self):
        """Return True when the move is queued for a bank payment but not
        settled yet.

        A settled move (amount_residual == 0) is never pending: the standard
        computation is authoritative for it.
        """
        self.ensure_one()
        if not self.is_invoice(include_receipts=True):
            return False
        if self.currency_id.is_zero(self.amount_residual):
            return False

        # Linked to a payment order (queued for payment on the bank).
        if self.line_ids.payment_line_ids:
            return True

        # Linked to a payment that is not settled against the bank yet.
        pending_payments = self.matched_payment_ids.filtered(
            lambda p: p.state in ("in_process", "paid")
        )
        if pending_payments:
            return True

        return False

    def _compute_payment_state(self):
        """Run the standard computation, then surface 'in_payment' for moves
        that are queued for a bank payment but not settled yet."""
        res = super()._compute_payment_state()

        pending = self.filtered(
            lambda m: m.payment_state == "not_paid"
            and m._is_pending_bank_settlement()
        )
        if pending:
            pending.payment_state = "in_payment"

        return res
