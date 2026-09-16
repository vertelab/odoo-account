# Copyright 2026 Vertel AB
# SPDX-License-Identifier: AGPL-3
{
    "name": "Vendor Bill Approval — Migration",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "One-shot migration from purchase_vendor_bill_approval",
    "author": "Vertel AB",
    "website": "https://vertel.se",
    "license": "AGPL-3",
    "depends": [
        "account_bill_approval",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": False,
    "application": False,
}
