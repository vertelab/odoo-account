{
    "name": "Account: Asset Management Report",
    "version": "1.0.1",
    "summary": "Depreciation board — pivot on asset lines, with department",
    "category": "Accounting",
    "author": "Vertel AB",
    "website": "https://vertel.se/apps/odoo-account/account_asset_management_report",
    "license": "AGPL-3",
    "maintainer": "Vertel AB",
    "repository": "https://github.com/vertelab/odoo-account",
    "description": "Adds a department on assets and a \"Depreciation Board\" pivot on asset lines, so depreciation can be followed per asset, per month, per department.",
    "depends": [
        "account_asset_management",
        "hr"
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "data": [
        "views/account_asset_line_view.xml",
        "views/account_asset_view.xml"
    ]
}
