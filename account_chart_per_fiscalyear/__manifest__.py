{
    "name": "Account: Chart of Accounts per Fiscal Year",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Chart of accounts versioned per fiscal year",
    "description": """
Manage chart of accounts per fiscal year.

Features:
- BAS chart templates importable from Excel
- Company chart variants (template + custom accounts)
- Diff view between chart versions when switching fiscal years
- Freeze chart snapshot when fiscal year is closed
- Apply chart changes when creating new fiscal year
    """,
    "author": "Vertel AB",
    "website": "https://www.vertel.se",
    "license": "AGPL-3",
    "depends": [
        "account_fiscal_year_vrtl",
        "account_chart_update",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_chart_template_views.xml",
        "views/account_chart_variant_views.xml",
        "views/account_fiscalyear_views.xml",
        "wizard/account_chart_diff_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
