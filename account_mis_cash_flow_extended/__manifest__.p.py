{
    "name": "Account: MIS Cash Flow Extended",
    "version": "1.0",
    "summary": "Cash flow forecast wizard — builds a forecast from the last three months of actuals",
    "category": "Accounting",
    "author": "Vertel AB",
    "website": "https://vertel.se/apps/odoo-account/account_mis_cash_flow_extended",
    "license": "AGPL-3",
    "maintainer": "Vertel AB",
    "repository": "https://github.com/vertelab/odoo-account",
    "description": "Adds a cash flow forecast on top of OCA's `mis_builder_cash_flow`: a wizard that reads the last three months of actuals per account, computes an average, and writes forecast lines for the coming periods.",
    "depends": [
        "account_mis_budget",
        "mis_builder",
        "account",
        "mis_builder_budget",
        "mis_builder_cash_flow"
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "data": [
        "security/ir.model.access.csv",
        "data/custom_account_classes.xml",
        "wizard/cash_flow_forecast_wizard.xml",
        "views/mis_cash_flow_forecast.xml",
        "views/mis_cash_flow_forecast_item.xml"
    ]
}
