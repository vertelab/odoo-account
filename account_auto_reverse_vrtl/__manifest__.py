{
    'name': 'Account: Auto Reverse Entries',
'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_auto_reverse_vrtl',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'license': 'AGPL-3',
    'summary': 'Automatically reverses accounting entries on a specified date.',
    'description': '''
Auto Reverse Entries
====================

    This module extends the account module to allow automatic reversal of journal entries on a specified date.

    Features:
    - Set a future date for automatic reversal of journal entries
    - Entries are automatically reversed without manual intervention
    - Helps in managing accruals, provisions, and temporary entries

    Features:

        - Automation: Scheduled jobs: Auto Reverse Invoices, Auto Reverse Invoices.
        - UI Integration: Extends 2 view(s) in the Odoo interface.
        - Extends Odoo: Builds on account.move.
    ''',
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
        'data/cron.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
