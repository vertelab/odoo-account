{
    'name': 'Auto Reverse Accounting Entries',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Automatically reverse accounting entries on a specified date',
    'description': """
This module extends the account module to allow automatic reversal of journal entries on a specified date.

Features:
- Set a future date for automatic reversal of journal entries
- Entries are automatically reversed without manual intervention
- Helps in managing accruals, provisions, and temporary entries
    """,
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
        'data/cron.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
