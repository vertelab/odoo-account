# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'Account: Payment Order Autogiro',
    'version': '18.0.1.0.0',
    'summary': 'Handles Autogiro direct debit for vendor bills with a pending state.',
    'description': '''
Payment Order Autogiro
======================

    Handles payment of vendor bills via Autogiro (the bank debits automatically),
so that they are not posted as paid prematurely.

Features:

    - Marks payment orders as pending until the bank confirms the debit.
    - Prevents premature reconciliation of vendor bills.
    ''',
    "version": "18.0.1.6.0",
    "license": "AGPL-3",
    "author": "Vertel Sverige AB",
    "website": "https://vertel.se/apps/odoo-account/account_payment_order_autogiro",
    "category": "Accounting",
    "depends": [
        "account_payment_order_pending",
        "l10n_se_credit_transfer",
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/account_payment_mode.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
