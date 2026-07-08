{
    'name': 'Account: Deferred Revenue Expenses',
    'version': '2.1.1',
    'summary': 'Deferred Revenue & Expenses with own models and stubs',
    'category': 'Accounting',
    'description': """
        Account Deferred Revenue Expenses
        =================================
        * Separate models: account.deferred, account.deferred.line, account.deferred.profile
        * Wizard to create deferred entries from invoice lines
        * Stub-based periodization with per-period posting
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_deferred_revenue_expenses',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'depends': ['account', 'analytic'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_deferred_profile_view.xml',
        'views/account_deferred_view.xml',
        'views/account_move_view.xml',
        'views/account_move_line_view.xml',
        'views/product_view.xml',
        'wizards/account_deferred_wizard_view.xml',
    ],
    'installable': True,
    'post_init_hook': 'post_init_hook',
    'auto_install': False,
}
