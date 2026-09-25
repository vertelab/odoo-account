{
    'name': 'Account: Commodity Price',
    'version': '18.0.1.0.0',
    'summary': 'Manages commodity prices, inventory revaluation and BOM integration.',
    'category': 'Accounting',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_commodity_price',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'description': '''
Commodity Price
===============

    Manage commodity prices (gold, silver, copper, oil, etc.) with:
    - Price history per commodity with quality/purity variants
    - Automatic price fetching via API (AurumRates, GoldAPI.io)
    - Inventory revaluation on price changes with accounting entries
    - BOM integration for raw material costing
    - Journal per commodity with gain/loss accounts
    - Kanban dashboard with real-time figures

    Similar to currency exchange rates (res.currency.rate) but for
    commodities with quality variants and inventory impact.

    Features:

        - Automation: Scheduled jobs: Fetch Commodity Prices, Gold, 24K.
        - Guided Wizards: Step-by-step dialogs for data entry.
        - Reports: Adds printable reports.
        - UI Integration: Extends 6 view(s) in the Odoo interface.
        - Extends Odoo: Builds on account.journal, account.move, display_name, product.commodity.
    ''',
    'depends': ['account', 'stock', 'stock_account', 'mrp'],
    'data': [
        'security/ir.model.access.csv',
        'data/product_commodity_demo.xml',
        'data/ir_cron.xml',
        'views/product_commodity_price_views.xml',
        'views/product_commodity_views.xml',
        'views/product_commodity_quality_views.xml',
        'views/product_template_views.xml',
        'views/account_journal_views.xml',
        'views/menu_views.xml',
        'wizard/commodity_revaluation_views.xml',
        'reports/commodity_report.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
