{
    'name': 'Account: Commodity Demo (3-Way Match)',
    'version': '1.0',
    'category': 'Accounting',
    'license': 'AGPL-3',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_commodity_demo',
    'summary': 'Demo data for gold and silver commodity purchasing with 3-way matching.',
    'description': '''
Commodity Demo (3-Way Match)
============================

    Self-contained demo module for gold/silver commodity purchasing,
        inventory receipt, and vendor bill 3-way matching.

    Creates:
        - 4 commodity products (gold wire 24K, gold plate 18K, silver wire 999,
          plating chemical)
        - 2 Swedish suppliers (Nordisk Komponent AB, Ädelmetall Nordic AB)
        - Gold (XAU) and Silver (XAG) commodities with quality variants
          (24K, 22K, 18K, 14K, 999 Silver)
        - Initial spot prices fetched from AurumRates API
        - 3 purchase orders with confirmed receipts
        - 3 vendor bills with auto-generated PDF invoice attachments
        - Partial receipt scenario for 3-way matching testing

    Dependencies:
        - account_commodity_price (commodity/quality/price models)
        - purchase (purchase orders, receipts)
        - stock (inventory valuation)

    Features:

        - Extends Odoo: Builds on account.move.
    ''',
    # account_commodity_price is an 18.0-only module (not ported to 19.0/20.0),
    # so this demo and its post_init_hook cannot be installed there.
    'installable': False,
    'depends': ['account_commodity_price', 'purchase', 'stock'],
    'post_init_hook': 'post_init_hook',
    'data': [
        'data/account_commodity_demo.xml',
    ],
    'demo': [],
    'application': False,
    'auto_install': False,
}
