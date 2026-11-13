# Copyright 2026 Vertel Sverige AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountPaymentMethodLine(models.Model):
    """Hide the interim account on a payment method line that defers booking.

    ``payment_account_id`` overrides the interim account for a single payment
    method line. For a ``pending_until_reconciliation`` method the account is
    never written to, so the field is hidden rather than left as a trap.
    """

    _inherit = "account.payment.method.line"

    is_pending_method = fields.Boolean(
        related="payment_method_id.pending_until_reconciliation",
        string="Pending Until Reconciliation",
    )
