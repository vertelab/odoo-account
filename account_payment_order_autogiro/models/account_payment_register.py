# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountPaymentRegister(models.TransientModel):
    """Adapter between the register-payment ("Pay") wizard and Autogiro.

    1. Auto-select: when the invoice being paid is an Autogiro vendor bill
       (payment mode -> method code 'autogiro') and the autogiro method line
       is available on the current journal, pre-select it in the wizard. This
       is a DEFAULT only -- the accountant may still change the method.

    2. Not settling: confirming marks the bills as awaiting bank settlement
       instead of paying them. No payment and no payment order are created:
       the bank transaction settles the bill directly, so there is nothing for
       a payment to book. The bill reads 'in_payment' until the bank statement
       is reconciled.

       This route deliberately bypasses account_payment_order entirely. The
       payment-order flow is unaffected: an order still creates its payments,
       which are left unbooked by account_payment_order_pending.
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
        """Flag the bills as awaiting bank settlement for Autogiro.

        When the wizard confirms outbound vendor bills paid with a
        pending-until-reconciliation method, no payment is created. The bills
        are flagged instead and read 'in_payment' until the bank transaction
        settles them.

        All other cases (non-pending method, inbound, already partially
        handled flows) keep the standard behaviour exactly.
        """
        if not self._is_autogiro_pending_pay():
            return super().action_create_payments()

        moves = self.line_ids.move_id
        moves.write({"is_pending_bank": True})
        moves._compute_payment_state()

        # Nothing is created, so there is no payment to redirect to: return to
        # the bills.
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": moves[:1].id,
            "target": "current",
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_autogiro_pending_pay(self):
        """True when this wizard confirm is an outbound pay with a
        pending-until-reconciliation method.

        Accepts one or several supplier invoices. The decision is based on the
        SELECTED payment method being pending-until-reconciliation, so it
        covers Autogiro vendor bills (payment mode autogiro) as well as
        invoices where the accountant selected the method manually — and any
        other pending method (IBAN, Bankgiro) that must also stay in_payment
        until reconciliation.
        """
        self.ensure_one()
        if not self.payment_method_line_id.payment_method_id.pending_until_reconciliation:
            return False
        if self.payment_type != "outbound":
            return False
        return bool(self.line_ids.move_id)
