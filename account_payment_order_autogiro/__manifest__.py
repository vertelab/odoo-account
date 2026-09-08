# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Account Payment Order - Autogiro",
    "summary": "Hantera autogiro för leverantörsfakturor med pending-state",
    "description": """
Autogiro för Leverantörsfakturor
=================================

Knyter leverantörsfakturor till autogiro-mandat så att de fångas upp
och inte hanteras som lösa fakturor.

Funktioner:
- Fält för autogiro-mandat på leverantörsfakturor
- Automatiskt 'pending'-beteende (ärver från account_payment_order_pending)
- Integration med OCA account_banking_mandate

Beroenden: account_payment_order_pending, account_banking_mandate,
account_banking_sepa_direct_debit, l10n_se_credit_transfer (payment method 'autogiro')
    """,
    "version": "18.0.1.1.0",
    "license": "AGPL-3",
    "author": "Vertel Sverige AB",
    "website": "https://vertel.se/apps/odoo-account/account_payment_order_autogiro",
    "category": "Accounting",
    "depends": [
        "account_payment_order_pending",
        "account_banking_mandate",
        "account_banking_sepa_direct_debit",
        "l10n_se_credit_transfer",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/account_payment_mode.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
