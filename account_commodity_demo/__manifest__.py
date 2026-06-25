{
    'name': 'Commodity Demo: Gold Plating 3-Way Match',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'license': 'AGPL-3',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_commodity_demo',
    'summary': 'Demo data for gold/silver commodity purchasing with 3-way matching',
    'description': '''
Commodity Purchase Flow Demo
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

All data is idempotent — safe to reinstall.
''',
    'depends': ['account_commodity_price', 'purchase', 'stock'],
    'data': [
        'data/account_commodity_demo.xml',
    ],
    'demo': [],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
