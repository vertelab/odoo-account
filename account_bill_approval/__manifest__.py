# Copyright 2026 Vertel AB
# SPDX-License-Identifier: AGPL-3
{
    "name": "Vendor Bill Approval",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "Approve vendor bills with freely selectable approvers",
    "author": "Vertel AB",
    "website": "https://vertel.se/apps/odoo-account/account_bill_approval",
    "license": "AGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/res_partner_views.xml",
        "wizards/vendor_bill_approval_user_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_bill_approval/static/src/components/*.js",
            "account_bill_approval/static/src/components/*.xml",
            "account_bill_approval/static/src/scss/*.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
}
