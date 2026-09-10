# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models
from odoo.tools.misc import clean_context


class AccountPaymentRegister(models.TransientModel):
    """Adapter between the register-payment ("Pay") wizard and Autogiro.

    Two concerns (see specs/ autogiro-payment / design.md):

    1. Auto-select: when the invoice being paid is an Autogiro vendor bill
       (payment mode -> method code 'autogiro') and the autogiro method line
       is available on the current journal, pre-select it in the wizard. This
       is a DEFAULT only -- the accountant may still change the method.
    2. Not settling: when the selected payment method has
       pending_until_reconciliation = True (Autogiro), confirming must NOT
       reconcile a payment that settles the invoice. The payment is created
       and posted (state 'in_process') but left UNRECONCILED, and the invoice
       is marked 'pending against bank' (see account.move
       is_autogiro_pending_bank), which surfaces it as in_payment until a bank
       statement outflow reconciles both to 'paid'.
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
        """Create + post the payment but skip reconciliation for Autogiro.

        When the wizard confirms outbound Autogiro vendor bills (single or
        multiple) that are not yet settled, create and post the bank payment
        (state 'in_process') exactly like the standard flow, but SKIP the
        reconciliation step so the invoices are not settled to 'paid'. They are
        instead parked 'pending against bank' (is_autogiro_pending_bank) and
        read in_payment until the bank outflow is reconciled.

        All other cases (non-pending method, inbound, already partially
        handled flows) keep the standard behaviour exactly.
        """
        if self._is_autogiro_pending_pay():
            # Run the standard create+post flow, but intercept before the
            # reconciliation step. We reuse the private helpers so the payment
            # is identical to a normal one (journal, method, currency, ...).
            to_process = []
            for batch in self.batches:
                batch_account = self._get_batch_account(batch)
                if (
                    self.require_partner_bank_account
                    and (not batch_account or not batch_account.allow_out_payment)
                ):
                    continue
                to_process.append({
                    'create_vals': self._create_payment_vals_from_batch(batch),
                    'to_reconcile': batch['lines'],
                    'batch': batch,
                })
            if not to_process:
                return super().action_create_payments()

            payments = self.with_context(
                clean_context(self.env.context)
            )._init_payments(to_process, edit_mode=False)
            self._post_payments(to_process, edit_mode=False)
            # A payment from an asset_cash account would be auto-set to 'paid'
            # by action_post(); for an Autogiro-pending pay it must stay
            # 'in_process' until the bank outflow is reconciled.
            payments.filtered(lambda p: p.state == 'paid').state = 'in_process'
            # Intentionally NO _reconcile_payments(): the invoices stay
            # in_payment (pending bank) until a bank statement reconcile.

            moves = self.line_ids.move_id
            moves.write({"is_autogiro_pending_bank": True})
            moves._compute_payment_state()

            action = {
                'name': 'Payments',
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'context': {'create': False},
            }
            if len(payments) == 1:
                action.update({'view_mode': 'form', 'res_id': payments.id})
            else:
                action.update({
                    'view_mode': 'list,form',
                    'domain': [('id', 'in', payments.ids)],
                })
            return action
        return super().action_create_payments()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_autogiro_pending_pay(self):
        """True when this wizard confirm is an outbound Autogiro pay that
        should be parked pending bank reconciliation (not settled).

        Accepts one or several supplier invoices. The decision is based on the
        SELECTED payment method being pending-until-reconciliation and the
        invoices being Autogiro vendor bills (payment mode autogiro, or a
        manually selected autogiro method on the wizard).
        """
        self.ensure_one()

        pending_method = (
            self.payment_method_line_id.payment_method_id.pending_until_reconciliation
        )
        if not pending_method:
            return False
        if self.payment_type != "outbound":
            return False

        moves = self.line_ids.move_id
        # Accept any outbound move paid with a pending-until-reconciliation
        # method. This covers Autogiro vendor bills (is_autogiro_vendor_bill)
        # as well as invoices without a payment_mode set where the accountant
        # manually selected the Autogiro method — and any other pending method
        # (IBAN, Bankgiro) that must also stay in_payment until reconciliation.
        return bool(moves)
