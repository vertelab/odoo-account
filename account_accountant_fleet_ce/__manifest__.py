{
    'name': 'Account: Accounting Fleet Bridge (CE)',
    'category': 'Accounting/Accounting',
    'summary': 'Adds fleet management to Community Edition accounting.',
    'description': '''
Accounting Fleet Bridge (CE)
============================

    Adds fleet management to Community Edition accounting.

    Features:

        - Extends Odoo: Builds on account.tax.
    ''',
    'version': '18.0.1.0.0',
    'depends': ['account_fleet', 'account_accountant_ce'],
    'data': [],
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_accountant_fleet_ce',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'installable': True,
    'auto_install': False,
}
