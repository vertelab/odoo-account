{
    "name": "Account: Asset Management Component",
    "version": "1.0",
    "summary": "Manage assets as components of a parent asset",
    "category": "Accounting",
    "author": "Vertel AB",
    "website": "https://vertel.se/apps/odoo-account/account_asset_management_component",
    "license": "AGPL-3",
    "maintainer": "Vertel AB",
    "repository": "https://github.com/vertelab/odoo-account",
    "description": "Groups several assets under one parent asset. The parent sums purchase value, salvage value, depreciation base, residual value and depreciated value from its components.",
    "depends": [
        "account_asset_management"
    ],
    "installable": true,
    "application": false,
    "auto_install": false,
    "data": [
        "security/ir.model.access.csv",
        "views/asset_parent_view.xml",
        "views/account_asset_view.xml"
    ]
}
