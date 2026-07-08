{
    "name": "Account: Fiscal Year MIS Bridge",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "MIS Builder integration for fiscal year balance reporting",
    "description": """
Bridge module connecting fiscal year closing results to MIS Builder reports.

Features:
- account.balance model: standalone balance records per fiscal year
- Create Balance action on fiscal year (delegates to OCA account_fiscal_year_closing)
- MIS report source 'account_balance' for reading balances directly
- No mis_builder_budget dependency — uses mis_builder core only
    """,
    "author": "Vertel AB",
    "website": "https://www.vertel.se",
    "license": "AGPL-3",
    "depends": [
        "account_fiscal_year_vrtl",
        "mis_builder",
        "account_fiscal_year_closing",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_fiscalyear_views.xml",
        "views/account_balance_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
