{
    'name': 'Account: 3-Way Match (CE)',
    'version': '18.0.1.0.0',
    'category': 'Supply Chain/Purchase',
    'summary': 'Adds 3-way matching on vendor bills for Community Edition.',
    'description': '''
3-Way Match (CE)
================

    In the manufacturing industry, people often receive the vendor bills before
    receiving their purchase, but they don't want to pay the bill until the goods
    have been delivered.

    The solution to this situation is to create the vendor bill when you get it
    (based on ordered quantities) but only pay the invoice when the received
    quantities (on the PO lines) match the recorded vendor bill.

    This module introduces a "release to pay" mechanism that marks for each vendor
    bill whether it can be paid or not.

    Each vendor bill receives one of the following three states:

    Features:

        - UI Integration: Extends 2 view(s) in the Odoo interface.
        - Extends Odoo: Builds on account.journal, account.move, account.move.line.
    ''',
    'depends': ['purchase'],
    'data': [
        'views/account_invoice_view.xml',
        'views/account_journal_dashboard_view.xml'
    ],
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_3way_match_ce',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'installable': True,
    'auto_install': False,
}
