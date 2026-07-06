# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # Extend mandate support for supplier invoices (autogiro for payables)
    supplier_mandate_id = fields.Many2one(
        "account.banking.mandate",
        string="Autogiro-mandat (leverantör)",
        ondelete="restrict",
        readonly=False,
        check_company=True,
        domain="[('state', '=', 'valid')]",
        help="Autogiro-mandat som ger leverantören rätt att dra betalningen "
        "automatiskt från företagets bankkonto.",
    )

    def _compute_payment_mode_id(self):
        """Override to also set supplier_mandate_id when autogiro is used."""
        res = super()._compute_payment_mode_id()
        for move in self:
            if (
                move.move_type in ("in_invoice", "in_receipt")
                and move.payment_mode_id
                and move.payment_mode_id.payment_method_id.code == "autogiro"
            ):
                # Auto-set supplier mandate from partner if available
                if not move.supplier_mandate_id:
                    move.supplier_mandate_id = move.partner_id.valid_mandate_id
        return res
