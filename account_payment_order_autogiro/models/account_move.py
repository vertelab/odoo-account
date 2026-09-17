# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountMove(models.Model):
    """Autogiro-specific marker on vendor bills.

    The pending state itself is handled by account_payment_order_pending: a
    bill linked to a payment made with a pending_until_reconciliation method
    reads 'in_payment' until the bank transaction settles it, and the payment
    follows without being booked. This module only needs to recognise an
    Autogiro vendor bill, so the "Pay" wizard can pre-select the method.
    """

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
