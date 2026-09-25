# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'Account: Payment Order Pending',
    'version': '18.0.1.0.0',
    'summary': "Keeps bills in an in-payment state until the bank reconciliation is done.",
    'description': '''
Payment Order Pending
=====================

    Lägger till en flagga `pending_until_reconciliation` på betalmetoder
    (account.payment.method). När flaggan är True:

    Implementation
    - `account.move._compute_payment_state()` överrids: en faktura som är kopplad
      till en betalorder (`line_ids.payment_line_ids`) eller till en betalning
      (`matched_payment_ids`) och som ännu inte är avstämd
      (`amount_residual != 0`) visas som `in_payment`.
    - `account.move.is_pending_bank` bär den väg där ingen betalning skapas alls:
      "Pay"-knappen med en pending-metod flaggar fakturan i stället för att skapa
      en betalning. Flaggan nollställs när fakturan är avstämd, eller när den
      lämnar `posted` (draft/avbruten) — annars skulle en återställd faktura
      fastna som "Pågående".
    - En annullerad betalorder räknas inte som väntande: OCA:s `action_cancel()`
      tar inte bort betalningsraderna, så orderns state kontrolleras. Utan det
      stannar fakturan som "Pågående" efter att ordern övergivits.
    - Betalningen synkas automatiskt: `account.payment._compute_state()` sätter
      betalningen till `paid` så snart alla avstämda fakturor är `paid`.

    1. Aktivera utvecklarläge
    2. Gå till Redovisning > Konfiguration > Betalmetoder
    3. Välj en betalmetod (t.ex. Swedish Credit Transfer)
    4. Bocka i 'Pending Until Reconciliation'
    5. När fakturan kopplas till en betalorder eller betalning visas den som
       "Pågående" och blir "Betald" först när banktransaktionen avstämts.

    Features:

        - Guided Wizards: Step-by-step dialogs for data entry.
        - UI Integration: Extends 3 view(s) in the Odoo interface.
        - Extends Odoo: Builds on account.move, account.payment, account.payment.method, account.payment.order.
    ''',
    "version": "18.0.1.8.0",
    "license": "AGPL-3",
    "author": "Vertel Sverige AB",
    "website": "https://vertel.se/apps/odoo-account/account_payment_order_pending",
    "category": "Accounting",
    "depends": [
        "account_payment_order",
    ],
    'data': [
        'views/account_payment_method_views.xml',
        'views/account_payment_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'tests': [
        'tests/test_payment_order_pending.py',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
