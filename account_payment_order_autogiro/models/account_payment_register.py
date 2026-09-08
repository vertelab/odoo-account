# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountPaymentRegister(models.TransientModel):
    """Adapter between the register-payment ("Pay") wizard and Autogiro.

    Two concerns (see specs/ autogiro-payment / design.md):

    1. Auto-select: when the invoice being paid is an Autogiro vendor bill
       (payment mode -> method code 'autogiro') and the autogiro method line
       is available on the current journal, pre-select it in the wizard. This
       is a DEFAULT only -- the accountant may still change the method.
    2. Not settling: when the selected payment method has
       pending_until_reconciliation = True (Autogiro), confirming must NOT
       post+reconcile a bank payment that settles the invoice. Instead the
       invoice is marked 'pending against bank' (see account.move
       is_autogiro_pending_bank), which surfaces it as in_payment until a bank
       statement outflow reconciles it to 'paid'.
    """

    _inherit = "account.payment.register"

    def _compute_payment_method_line_id(self):
        """Pre-select the Autogiro method line for Autogiro vendor bills.

        Only selects when the autogiro line is available on the resolved
        journal; never forces/creates it, so non-Autogiro invoices and
        journals without autogiro are untouched and the field stays editable.
        """
        res = super()._compute_payment_method_line_id()
        for wizard in self:
            moves = wizard.line_ids.move_id
            available = wizard.available_payment_method_line_ids
            if (
                available
                and moves
                and all(move.is_autogiro_vendor_bill for move in moves)
                and wizard.payment_type == "outbound"
            ):
                autogiro_lines = available.filtered(
                    lambda line: line.code == "autogiro"
                    or line.payment_method_id.code == "autogiro"
                )
                if autogiro_lines:
                    wizard.payment_method_line_id = autogiro_lines[:1]
        return res

    def action_create_payments(self):
        """Do not post/reconcile towards the bank for Autogiro-pending pays.

        When the wizard confirms a single Autogiro vendor bill that is not yet
        settled, skip the standard create&post&reconcile and instead park the
        invoice in the 'pending against bank' state. It then reads in_payment
        and only becomes 'paid' once the bank outflow is reconciled.

        All other cases (non-Autogiro method, multi-invoice batch, already
        partially handled flows, inbound) keep the standard behaviour exactly.
        """
        if self._is_autogiro_pending_pay():
            moves = self.line_ids.move_id
            moves.write({"is_autogiro_pending_bank": True})
            moves._compute_payment_state()
            return True
        return super().action_create_payments()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_autogiro_pending_pay(self):
        """True when this wizard confirm is a single outbound Autogiro pay
        that should be parked pending bank reconciliation (not settled)."""
        self.ensure_one()

        pending_method = (
            self.payment_method_line_id.payment_method_id.pending_until_reconciliation
        )
        if not pending_method:
            return False
        if self.payment_type != "outbound":
            return False

        moves = self.line_ids.move_id
        return bool(
            moves
            and len(moves) == 1
            and moves.is_autogiro_vendor_bill
        )
