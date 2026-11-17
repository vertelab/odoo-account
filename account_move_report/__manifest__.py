{
    "name": "Account Move Report",
    "version": "1.0",
    "summary": "Print Account Moves",
    "category": "Accounting",
    "author": "Vertel AB",
    "website": "https://vertel.se/apps/odoo-account/account_move_report",
    "license": "AGPL-3",
    "maintainer": "Vertel AB",
    "repository": "https://github.com/vertelab/odoo-account",
    "description": "Adds a report that prints a journal entry with account, partner, analytic account, debit, credit and taxes per line.",
    "depends": [
        "account"
    ],
    "installable": true,
    "application": false,
    "auto_install": false,
    "data": [
        "report/account_move_report.xml"
    ]
}
