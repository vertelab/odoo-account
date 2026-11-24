# Copyright 2026 Vertel Sverige AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'Account: Tagetik Fields',
    'version': '18.0.1.0.1',
    'summary': 'Adds Tagetik Code and Tagetik Text to accounts and journal items.',
    'category': 'Accounting/Accounting',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_tagetik',
    'license': 'AGPL-3',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'depends': [
        'account',
    ],
    'data': [
        'views/account_account_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
