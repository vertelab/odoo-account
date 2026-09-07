# Copyright 2026 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Account Reconcile Enhanced",
    "summary": """
        Enhanced reconciliation features for OCA reconcile:
        multi-account transfer, tax write-off, edit mode, auto-reconcile wizard,
        regex amount extraction, and enhanced matching rules.""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Vertel Sverige AB, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-reconcile",
    "depends": [
        "account_reconcile_oca",
        "account_reconcile_model_oca",
        "account_reconcile_wizard",
    ],
    "excludes": ["account_accountant"],
    "data": [
        "security/ir.model.access.csv",
        "data/account_reconcile_model_fee.xml",
        "wizard/account_reconcile_wizard.xml",
        "wizard/account_auto_reconcile_wizard.xml",
        "views/account_reconcile_views.xml",
    ],
    "assets": {
        "web.assets_backend": [],
    },
}
