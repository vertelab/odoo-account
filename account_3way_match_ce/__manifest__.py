{
    'name': 'Vendor Bill: Release to Pay (CE)',
    'category': 'Supply Chain/Purchase',
    'summary': '3-way matching on vendor bills for Community Edition',
    'description': """
Manage 3-way matching on vendor bills
=====================================

In the manufacturing industry, people often receive the vendor bills before
receiving their purchase, but they don't want to pay the bill until the goods
have been delivered.

The solution to this situation is to create the vendor bill when you get it
(based on ordered quantities) but only pay the invoice when the received
quantities (on the PO lines) match the recorded vendor bill.

This module introduces a "release to pay" mechanism that marks for each vendor
bill whether it can be paid or not.

Each vendor bill receives one of the following three states:

    - Yes (The bill can be paid)
    - No (The bill cannot be paid, nothing has been delivered yet)
    - Exception (Received and invoiced quantities differ)
    """,
    'depends': ['purchase'],
    'data': [
        'views/account_invoice_view.xml',
        'views/account_journal_dashboard_view.xml'
    ],
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_3way_match_ce',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'installable': True,
    'auto_install': False,
}
