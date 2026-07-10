# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Global default for pending_until_reconciliation on new payment methods
    pending_until_reconciliation_default = fields.Boolean(
        string="Pending Until Reconciliation (standard)",
        help="När aktiverat: alla NYA betalmetoder får "
        "'Pending Until Reconciliation' som standard.\n"
        "Befintliga betalmetoder påverkas inte — ändra per metod "
        "under Redovisning > Konfiguration > Betalmetoder.",
        config_parameter='account_payment_order_pending.default_enabled',
        default=True,
    )
