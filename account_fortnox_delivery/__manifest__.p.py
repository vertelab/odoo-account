{
    "name": "Account: Fortnox Integration Delivery",
    "version": "1.0",
    "summary": "Glue module — sends the delivery method and delivery date to Fortnox",
    "category": "Accounting",
    "author": "Vertel AB",
    "website": "https://vertel.se/apps/odoo-account/account_fortnox_delivery",
    "license": "AGPL-3",
    "maintainer": "Vertel AB",
    "repository": "https://github.com/vertelab/odoo-account",
    "description": "Adds a Fortnox code on delivery carriers and sends it as WayOfDelivery on the Fortnox invoice, together with the actual delivery date from the picking.",
    "depends": [
        "account_fortnox",
        "delivery"
    ],
    "installable": true,
    "application": false,
    "auto_install": true,
    "data": [
        "views/delivery_carrier_view.xml"
    ]
}
