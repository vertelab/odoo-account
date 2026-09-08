# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Account Payment Order - Autogiro",
    "summary": "Hantera autogiro för leverantörsfakturor med pending-state",
    "description": """
Autogiro för Leverantörsfakturor
=================================

Hanterar betalning av leverantörsfakturor via Autogiro (banken drar
automatiskt) så att de inte bokförs som betalda i förtid.

Funktioner:
- Betala Autogiro-faktura via Pay-menyn sätter fakturan till 'Pågående'
  (in_payment), inte 'Betald' (paid)
- Betald sker först när en banktransaktion avstäms mot fakturan
- Autogiro-betalmetoden förväljs automatiskt i Pay-wizard när fakturans
  betalningssätt är Autogiro (går fortfarande att ändra)
- Inget mandat-fält krävs på leverantörsfakturan

Beroenden: account_payment_order_pending, l10n_se_credit_transfer
(payment method 'autogiro')
    """,
    "version": "18.0.1.2.0",
    "license": "AGPL-3",
    "author": "Vertel Sverige AB",
    "website": "https://vertel.se/apps/odoo-account/account_payment_order_autogiro",
    "category": "Accounting",
    "depends": [
        "account_payment_order_pending",
        "l10n_se_credit_transfer",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/account_payment_mode.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
