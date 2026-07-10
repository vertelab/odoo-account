# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    pending_until_reconciliation = fields.Boolean(
        string="Pending Until Reconciliation",
        default=False,
        help="When enabled, payment orders using this method will NOT post "
        "or reconcile payments upon upload. Invoices stay 'in_payment' "
        "(pågående) until bank statement reconciliation.\n"
        "Applicable for IBAN, Bankgiro, Autogiro and other order-based "
        "payments where the invoice should not be marked as paid when "
        "the payment file is generated/uploaded.",
    )
