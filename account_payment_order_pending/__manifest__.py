# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Account Payment Order Pending State",
    "summary": "Håll fakturor som 'pågående' (in_payment) tills bankavstämning för betalorder",
    "description": """
Pending State för Betalorder
============================

Lägger till en flagga `pending_until_reconciliation` på betalmetoder
(account.payment.method). När flaggan är True:

- Betalorderns `generated2uploaded()` hoppar över `post_and_reconcile()`
- Inga betalningar bokförs eller matchas vid uppladdning
- Fakturor förblir i status "in_payment" (pågående)
- Leverantörsskulden kvarstår tills bankkontoutdrag avstämts

Användning
----------
1. Aktivera utvecklarläge
2. Gå till Redovisning > Konfiguration > Betalmetoder
3. Välj en betalmetod (t.ex. Swedish Credit Transfer)
4. Bocka i 'Pending Until Reconciliation'
5. När betalorder skapas med denna metod kommer fakturor inte
   att märkas som betalda förrän bankavstämning sker.

Beroenden: account_payment_order (OCA/bank-payment)
    """,
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Vertel AB",
    "website": "https://vertel.se/apps/odoo-account/account_payment_order_pending",
    "category": "Accounting",
    "depends": [
        "account_payment_order",
    ],
    "data": [
        "views/account_payment_method_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
