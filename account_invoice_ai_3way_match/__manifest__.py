{
    'name': 'Account: Invoice AI 3-Way Match Bridge',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Bridges AI invoice scanning with 3-way purchase matching.',
    'description': '''
Invoice AI 3-Way Match Bridge
=============================

    Glue module that automatically links AI-scanned vendor bills to purchase
        orders so the 3-way match (PO vs receipt vs invoice) works end-to-end.

    When both account_invoice_ai and account_3way_match_ce are installed, this
        module auto-installs and:

    Features:

        - Extends Odoo: Builds on ai.quest.
    ''',
    'depends': ['account_invoice_ai', 'account_3way_match_ce'],
    'data': [],
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_invoice_ai_3way_match',
    'license': 'AGPL-3',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'installable': True,
    'auto_install': True,
}
