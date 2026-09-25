{
    'name': 'Account: Deferred Revenue Expenses',
    'version': '18.0.2.7.0',
    'summary': 'Handles deferred revenue and expenses with dedicated models.',
    'category': 'Accounting',
    'description': '''
Deferred Revenue Expenses
=========================

    Account Deferred Revenue Expenses
            =================================
            * Separate models: account.deferred, account.deferred.line, account.deferred.profile
            * Wizard to create deferred entries from invoice lines
            * Stub-based periodization with per-period posting

    Features:

        - Automation: Scheduled jobs: Deferred: post due periodisation stubs, Kontorshyra 3 mån, Lagerhyra 3 mån.
        - Guided Wizards: Step-by-step dialogs for data entry.
        - UI Integration: Extends 6 view(s) in the Odoo interface.
        - Extends Odoo: Builds on account.deferred, account.deferred.line, account.deferred.profile, account.move.
    ''',
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
