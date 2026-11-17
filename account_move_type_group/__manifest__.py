{
    "name": "Account: Move Type Group",
    "version": "1.0",
    "summary": "Restrict journal entries per direction (in-bound vs out-bound)",
    "category": "Accounting",
    "author": "Vertel AB",
    "website": "https://vertel.se/apps/odoo-account/account_move_type_group",
    "license": "AGPL-3",
    "maintainer": "Vertel AB",
    "repository": "https://github.com/vertelab/odoo-account",
    "description": "Adds two permission groups \u2014 In-Type Invoices and Out-Type Invoices \u2014 and lets each journal be assigned to one of them. A user only sees the journal entries of the journals whose group they belong to.\n\nPorted from 16.0. The 16.0 module defined `account.journal.group_id` itself; Odoo 18 owns `account.journal.group` for the multi-ledger filter, so this version uses `move_type_group_id`. The dependency on `account_period_vrtl` was removed \u2014 the module never used it.",
    "depends": ["account"],
    "data": ["security/security.xml", "views/account_view.xml"],
    "installable": True,
    "application": False,
    "auto_install": False
}
