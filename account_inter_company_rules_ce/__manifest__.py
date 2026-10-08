{
    'name': 'Account: Inter Company Rules (CE)',
    'version': '18.0.1.0.0',
    'summary': 'Adds intercompany sale, purchase and invoice rules for Community Edition.',
    'category': 'Productivity',
    'description': '''
Inter Company Rules (CE)
========================

    Module for synchronization of Documents between several companies. For example, this allow you to have a Sales Order created automatically when a Purchase Order is validated with another company of the system as vendor, and inversely.

    Features:

        - UI Integration: Extends 2 view(s) in the Odoo interface.
        - Extends Odoo: Builds on account.journal, account.move, account.move.line, account.move.send.
    ''',
    'depends': [
        'account',
    ],
    'data': [
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_inter_company_rules_ce',
    'license': 'AGPL-3',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-account',
}
