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

    def _compute_payment_mode_id(self):
        """Override to also set supplier_mandate_id when autogiro is used."""
        res = super()._compute_payment_mode_id()
        for move in self:
            if move.is_autogiro_vendor_bill:
                # Auto-set supplier mandate from partner if available
                if not move.supplier_mandate_id:
                    move.supplier_mandate_id = move.partner_id.valid_mandate_id
        return res
