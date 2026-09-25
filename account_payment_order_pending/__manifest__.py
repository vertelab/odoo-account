# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'Account: Payment Order Pending',
    'version': '18.0.1.0.0',
    'summary': "Keeps bills in an in-payment state until the bank reconciliation is done.",
    'description': '''
Payment Order Pending
=====================

    Adds a ``pending_until_reconciliation`` flag to payment methods
(account.payment.method).

When the flag is set, payment orders using that method stay pending until
they are reconciled.
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
