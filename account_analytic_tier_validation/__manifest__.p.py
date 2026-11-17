{
    "name": "Account: Analytic Tier Validation",
    "version": "1.0",
    "summary": "Derive the invoice's reviewers from the analytic distribution (cost center)",
    "category": "Accounting",
    "author": "Vertel AB",
    "website": "https://vertel.se/apps/odoo-account/account_analytic_tier_validation",
    "license": "AGPL-3",
    "maintainer": "Vertel AB",
    "repository": "https://github.com/vertelab/odoo-account",
    "description": "Adds a reviewer on analytic accounts and computes, on each invoice, the set of reviewers from the analytic distribution of its lines.\n\nPorted from 16.0. The 16.0 module depended on `account_move_tier_validation`, which does not exist in this repository, on any branch, or in OCA. This version depends on `base_tier_validation` directly instead.",
    "depends": ["analytic", "account", "base_tier_validation"],
    "data": ["views/account_analytics_view.xml", "views/account_move_view.xml"],
    "installable": true,
    "application": false,
    "auto_install": false
}
