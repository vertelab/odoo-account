# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountMove(models.Model):
    """Mark a bill as awaiting bank settlement.

    A bill paid with a `pending_until_reconciliation` method reads 'in_payment'
    until the bank confirms the movement. Two routes lead there:

    * a payment order, where the bill is linked through payment lines;
    * the "Pay" button, where no payment and no payment order are created at
      all — the bill is simply flagged and the bank transaction settles it
      directly.

    The flag covers the second route. It is cleared as soon as the bill is
    settled, so the derived state takes over.
    """

    _inherit = "account.move"

    is_pending_bank = fields.Boolean(
        string="Väntar på bank",
        copy=False,
        help="Satt när fakturan skickats till banken via Pay-knappen med en "
        "betalmetod som väntar på avstämning. Fakturan visas som 'Pågående' "
        "tills banktransaktionen avstämts, då flaggan nollställs.",
    )

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

        # Flagged by the "Pay" button (no payment, no payment order).
        if self.is_pending_bank:
            return True

        # Linked to a payment order (queued for payment on the bank).
        if self.line_ids.payment_line_ids:
            return True

        # Linked to a payment that is not settled against the bank yet. A
        # payment made with the "Pay" button stays 'draft' until the bank
        # confirms the movement, so 'draft' counts as pending too.
        pending_payments = self.matched_payment_ids.filtered(
            lambda p: p.state in ("draft", "in_process", "paid")
            and p._is_pending_order_payment()
        )
        if pending_payments:
            return True

        return False

    def _compute_payment_state(self):
        """Run the standard computation, then surface 'in_payment' for moves
        that are queued for a bank payment but not settled yet."""
        res = super()._compute_payment_state()

        # A settled bill no longer waits for the bank: clear the flag so the
        # derived state is authoritative from now on.
        for move in self.filtered(
            lambda m: m.is_pending_bank
            and m.currency_id.is_zero(m.amount_residual)
        ):
            move.is_pending_bank = False

        pending = self.filtered(
            lambda m: m.payment_state == "not_paid"
            and m._is_pending_bank_settlement()
        )
        if pending:
            pending.payment_state = "in_payment"

        return res
