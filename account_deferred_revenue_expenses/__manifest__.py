{
    'name': 'Account: Deferred Revenue Expenses',
    'version': '18.0.2.5.0',
    'summary': 'Deferred Revenue & Expenses with own models and stubs',
    'category': 'Accounting',
    'description': """
        Account Deferred Revenue Expenses
        =================================
        * Separate models: account.deferred, account.deferred.line, account.deferred.profile
        * Wizard to create deferred entries from invoice lines
        * Stub-based periodization with per-period posting
    """,
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_deferred_revenue_expenses',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'depends': ['account', 'analytic'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_deferred_auto_post.xml',
        'views/account_deferred_profile_view.xml',
        'views/account_deferred_view.xml',
        'views/account_move_view.xml',
        'views/account_move_line_view.xml',
        'views/product_view.xml',
        'views/res_config_settings_views.xml',
        'wizards/account_deferred_wizard_view.xml',
    ],
    'installable': True,
    'post_init_hook': 'post_init_hook',
    'auto_install': False,
}
