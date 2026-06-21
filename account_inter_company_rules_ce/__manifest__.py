{
    'name': 'Inter Company Module for Sale/Purchase Orders and Invoices (CE)',
    'version': '1.0',
    'summary': 'Intercompany SO/PO/INV rules for Community Edition',
    'category': 'Productivity',
    'description': ''' Module for synchronization of Documents between several companies. For example, this allow you to have a Sales Order created automatically when a Purchase Order is validated with another company of the system as vendor, and inversely.

    Supported documents are invoices/credit notes.
''',
    'depends': [
        'account',
    ],
    'data': [
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_inter_company_rules_ce',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
}
