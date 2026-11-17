{
    "name": "Account Invoice Multi Currency",
    "version": "1.0",
    "summary": "Show the invoice totals in additional currencies",
    "category": "Accounting",
    "author": "Vertel AB",
    "website": "https://vertel.se/apps/odoo-account/account_invoice_multi_currency",
    "license": "AGPL-3",
    "maintainer": "Vertel AB",
    "repository": "https://github.com/vertelab/odoo-account",
    "description": "Shows the invoice totals in the currencies chosen on the company, in addition to the invoice's own currency.\n\nPorted from 14.0. The 14.0 version replaced the whole total block; Odoo 18 computes totals through `account.document_tax_totals`, so this version adds a block after the ordinary totals instead.",
    "depends": [
        "account"
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "data": [
        "views/report_invoice.xml",
        "views/res_config_settings_views.xml"
    ]
}
