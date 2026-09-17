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
- Betalningarna bokförs men matchas inte mot fakturorna vid uppladdning
- Fakturor som är kopplade till en betalning eller betalorder visas som
  "Pågående" (in_payment) tills banktransaktionen är avstämd
- När banken bekräftar avstäms fakturan automatiskt och blir "Betald"
  (paid); betalningen följer fakturans status

Implementation
--------------
- `account.move._compute_payment_state()` överrids: en faktura som är kopplad
  till en betalorder (`line_ids.payment_line_ids`) eller till en betalning
  (`matched_payment_ids`) och som ännu inte är avstämd
  (`amount_residual != 0`) visas som `in_payment`. Ingen extra flagga lagras —
  tillståndet härleds ur de länkar som redan finns.
- `account.partial.reconcile.create()` överrids: när en banktransaktion
  avstäms mot en betalning avstäms även fakturans rad mot betalningens rad,
  precis som `AccountPaymentOrder.post_and_reconcile()` gör i standardflödet.
  Hooken ligger på Odoo-kärnan, inte på någon avstämnings-UI, så den fångar
  alla vägar (account_reconcile_oca, standardwidgeten eller ett direkt
  `reconcile()`-anrop).
- Betalningen synkas automatiskt: `account.payment._compute_state()` sätter
  betalningen till `paid` så snart alla avstämda fakturor är `paid`.

Användning
----------
1. Aktivera utvecklarläge
2. Gå till Redovisning > Konfiguration > Betalmetoder
3. Välj en betalmetod (t.ex. Swedish Credit Transfer)
4. Bocka i 'Pending Until Reconciliation'
5. När fakturan kopplas till en betalorder eller betalning visas den som
   "Pågående" och blir "Betald" först när banktransaktionen avstämts.

Beroenden: account_payment_order (OCA/bank-payment)
    """,
    "version": "18.0.1.5.0",
    "license": "AGPL-3",
    "author": "Vertel Sverige AB",
    "website": "https://vertel.se/apps/odoo-account/account_payment_order_pending",
    "category": "Accounting",
    "depends": [
        "account_payment_order",
    ],
    "data": [
        "views/account_payment_method_views.xml",
        "views/account_payment_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "tests": [
        "tests/test_payment_order_pending.py",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
