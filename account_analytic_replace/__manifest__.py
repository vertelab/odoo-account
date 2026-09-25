# account_analytic_replace/__manifest__.py
{
    'name': 'Account: Analytic Replace',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Replaces analytic plans and accounts with automatic search redirection.',
    'description': '''
Analytic Replace
================

    Adds replace functionality to Analytic Plans:
            - Set current plan to Unavailable
            - Create new replacement plan
            - Copy all analytic accounts
            - Track replacements
            - Search redirection from old to new

    Features:

        - UI Integration: Extends 2 view(s) in the Odoo interface.
        - Extends Odoo: Builds on account.analytic.account, account.analytic.plan, account.analytic.replace.wizard.
    ''',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_analytic_replace',
    'depends': ['account','analytic'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_analytic_plan_views.xml',
        'views/account_analytic_replace_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
}
