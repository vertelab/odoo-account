{
    "name": "MIS Period Wizard",
    "version": "1.0",
    "summary": "Create the comparison periods (opening balance, period, closing balance) for a MIS report",
    "category": "Accounting",
    "author": "Vertel AB",
    "website": "https://vertel.se/apps/odoo-account/account_mis_period_wizard",
    "license": "AGPL-3",
    "maintainer": "Vertel AB",
    "repository": "https://github.com/vertelab/odoo-account",
    "description": "Adds a \"Choose Period\" action on MIS report instances. Given a period, it fills the report with three comparison columns: opening balance, the period itself, and closing balance.\n\nPorted from 14.0. The 14.0 version read `account.period.code` and filtered on `special`; Odoo 18's period is a date.range without either field.",
    "depends": [
        "account_fiscal_year_vrtl",
        "mis_builder"
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "data": [
        # #if VERSION >= "20.0"
        "security/ir.access.csv",
        # #else
        "security/ir.model.access.csv",
        # #endif
        "wizard/account_mis_period_wizard.xml"
    ]
}
