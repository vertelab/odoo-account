# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    is_autogiro_vendor_bill = fields.Boolean(
        string="Autogiro leverantörsfaktura",
        compute="_compute_is_autogiro_vendor_bill",
        store=False,
        help="Tekniskt fält: True när payment_mode har payment_method.code == 'autogiro' "
        "och move_type är in_invoice/in_receipt.",
    )

    @api.depends("payment_mode_id", "payment_mode_id.payment_method_id", "move_type")
    def _compute_is_autogiro_vendor_bill(self):
        for move in self:
            try:
                code = move.payment_mode_id.payment_method_id.code
            except Exception:
                code = False
            move.is_autogiro_vendor_bill = (
                move.move_type in ("in_invoice", "in_receipt")
                and code == "autogiro"
            )

    is_autogiro_pending_bank = fields.Boolean(
        string="Autogiro pågående mot bank",
        copy=False,
        help="Tekniskt/funktionellt fält: när True har fakturan bekräftats för "
        "Autogiro-betalning via Pay-menyn och väntar på bankavstämning. "
        "Fakturan visas som 'Pågående' (in_payment) tills en banktransaktion "
        "avstämts mot den, då den blir 'Betald' (paid) och flaggan nollställs.",
    )

    def _compute_payment_state(self):
        """Run standard computation, then surface 'in_payment' for invoices that
        are pending bank reconciliation on an Autogiro payment.

        Odoo 18 only derives 'in_payment' from real reconciles / matched
        payments. A bill confirmed for Autogiro via the Pay wizard carries no
        such artifact until the bank outflow is reconciled, so it would
        otherwise stay 'not_paid'. This override (mirroring the pattern proven
        in account_payment_order_pending) forces 'in_payment' from the stored
        is_autogiro_pending_bank signal until a reconcile settles the invoice,
        at which point the derived state wins and the flag is cleared.
        """
        res = super()._compute_payment_state()

        for move in self:
            if move.is_autogiro_pending_bank:
                if move.payment_state == "not_paid":
                    # Not yet settled by a bank reconcile -> show as pending.
                    move.payment_state = "in_payment"
                else:
                    # A reconcile settled (or partially reconciled) the bill.
                    # Stop forcing in_payment and forget the pending signal so
                    # the derived state (paid/partial/...) is authoritative.
                    move.is_autogiro_pending_bank = False

        return res
