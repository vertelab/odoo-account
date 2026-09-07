# account_analytic_replace/__manifest__.py
{
    'name': 'Account Analytic Replace',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Replace Analytic Plans and Accounts with automatic search redirection',
    'description': """
        Adds replace functionality to Analytic Plans:
        - Set current plan to Unavailable
        - Create new replacement plan
        - Copy all analytic accounts
        - Track replacements
        - Search redirection from old to new
    """,
    'author': 'Vertel Sverige AB',
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
