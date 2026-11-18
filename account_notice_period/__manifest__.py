{
    "name": "Account: Notice Period",
    "version": "1.0",
    "summary": "Notice period text on payment terms, shown in the invoice footer",
    "category": "Accounting",
    "author": "Vertel AB",
    "website": "https://vertel.se/apps/odoo-account/account_notice_period",
    "license": "AGPL-3",
    "maintainer": "Vertel AB",
    "repository": "https://github.com/vertelab/odoo-account",
    "description": "Adds a free-text notice period note on payment terms. The note is printed in the footer of invoices and sale orders, together with the company registry number.",
    "depends": [
        "account"
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "data": [
        "views/payment_term_view.xml",
        "views/external_layout.xml"
    ]
}
