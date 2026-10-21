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
        compute="_compute_is_pending_bank",
        store=True,
        readonly=False,
        help="Satt när fakturan väntar på att banken ska stämma av betalningen. "
        "Gäller både Pay-knappen (flaggan skrivs direkt) och betalorder "
        "(härleds från betalningsraderna). Fakturan visas som 'Pågående' "
        "tills banktransaktionen avstämts.",
    )

    # The manual flag written by the Pay button. Kept separate from the stored
    # computed field above so a payment order can never be "un-flagged" by a
    # recompute: the compute ORs this value in.
    is_pending_bank_manual = fields.Boolean(
        string="Väntar på bank (manuellt)",
        copy=False,
        help="Tekniskt fält: sätts av Pay-knappen när ingen betalorder finns. "
        "Slås ihop med betalorder-signalen i is_pending_bank.",
    )

    @api.depends(
        "is_pending_bank_manual",
        "state",
        "amount_residual",
        "line_ids.payment_line_ids",
        "line_ids.payment_line_ids.order_id.state",
        "matched_payment_ids.state",
    )
    def _compute_is_pending_bank(self):
        """Keep the stored flag in sync with both routes into the bank.

        The Pay button writes is_pending_bank_manual; a payment order links the
        bill through payment lines. Storing the union means the form view can
        simply read the field, and the Pay button disappears for both routes.
        """
        for move in self:
            move.is_pending_bank = move._is_pending_bank_settlement()


    def _is_pending_bank_settlement(self):
        """Return True when the move is queued for a bank payment but not
        settled yet.

        A settled move (amount_residual == 0) is never pending: the standard
        computation is authoritative for it. Neither is a move that is no
        longer posted: a draft or cancelled bill is not waiting for the bank,
        it is simply not booked. Without that guard the flag (and a cancelled
        payment order) would keep a draft/cancelled bill reading 'in_payment'
        forever, with no way out in the UI.
        """
        self.ensure_one()
        if not self.is_invoice(include_receipts=True):
            return False
        if self.state != "posted":
            return False
        if self.currency_id.is_zero(self.amount_residual):
            return False

        # Flagged by the "Pay" button (no payment, no payment order).
        if self.is_pending_bank_manual:
            return True

        # Linked to a payment order that is still queued for the bank. A
        # cancelled order keeps its payment lines (OCA's action_cancel does not
        # unlink them), so the order state must be checked — otherwise the bill
        # stays 'in_payment' after the order is abandoned.
        queued_lines = self.line_ids.payment_line_ids.filtered(
            lambda line: line.order_id.state != "cancel"
        )
        if queued_lines:
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

    @api.depends(
        "line_ids.payment_line_ids",
        "line_ids.payment_line_ids.state",
        "is_pending_bank_manual",
    )
    def _compute_payment_state(self):
        """Run the standard computation, then surface 'in_payment' for moves
        that are queued for a bank payment but not settled yet.

        The extra dependencies matter: core does not depend on the payment
        lines or on our flag, so without them a bill would keep its
        'in_payment' value after the payment order was cancelled (the payment
        lines stay linked, only their state changes) or after the flag was
        cleared elsewhere.
        """
        res = super()._compute_payment_state()

        # A settled bill no longer waits for the bank: clear the manual flag so
        # the derived state is authoritative from now on. A bill that is no
        # longer posted does not wait for the bank either — it was reset to
        # draft or cancelled, and the flag would otherwise keep it 'in_payment'
        # with no way to clear it from the UI.
        for move in self.filtered(
            lambda m: m.is_pending_bank_manual
            and (
                m.currency_id.is_zero(m.amount_residual)
                or m.state != "posted"
            )
        ):
            move.is_pending_bank_manual = False

        pending = self.filtered(
            lambda m: m.payment_state == "not_paid"
            and m._is_pending_bank_settlement()
        )
        if pending:
            pending.payment_state = "in_payment"

        return res
