{
    "name": "Account: Fiscal Year",
    # Version ledger: 18.0 = Odoo version. 1 = Major. 2 = Minor. 0 = Patch.
    #
    # Do NOT flatten this to '1.0'. Odoo expands '1.0' to 18.0.1.0, and a
    # database already on 18.0.1.1.0 then never sees a version increase --
    # so migrations/18.0.1.2.0/pre-adopt-types.py never runs, the data file
    # tries to create the date range types a second time, and the registry
    # dies on date_range_type_date_range_type_uniq.
    #
    # The version must stay ahead of the highest migrations/ directory.
    "version": '1.2.0',
    "category": "Accounting/Accounting",
    "summary": "Fiscal years with monthly periods, period closing, and hash-locking",
    "description": """
Generic fiscal year and period management module.

Features:
- Fiscal years (account.fiscal.year) with date_from/date_to
- Monthly periods via date_range delegation inheritance
- Per-journal period closing
- Optional hash-locking on period close
- Strict period validation on account.move operations
- Server action for scheduled period closing
- Fiscal Year and Month date range types (Quarter/Week live in l10n_se_date_ranges)
- Balance/closing via bridge module (account_fiscal_year_mis + OCA account_fiscal_year_closing)
    """,
    "author": "Vertel AB",
    "website": "https://www.vertel.se",
    "license": "AGPL-3",
    "depends": [
        "account",
        "account_fiscal_year",
        "date_range",
        "cron_tick",
    ],
    "data": [
        "security/security.xml",
        # #if VERSION >= "20.0"
        "security/ir.access.csv",
        # #else
        "security/ir.model.access.csv",
        # #endif
        "data/date_range_type_data.xml",
        "data/ir_server_action.xml",
        "data/cron_task.xml",
        "views/account_fiscalyear_views.xml",
        "views/account_period_views.xml",
        "views/account_move_views.xml",
        "views/account_move_line_views.xml",
        "views/account_period_exception_views.xml",
        "views/account_journal_views.xml",
        "views/res_config_settings_views.xml",
        # "views/onboarding_template.xml",  # BORTTAGEN 2026-10-29: account.onboarding.step saknas i Odoo 18
        "wizard/account_period_close_view.xml",
        "wizard/account_fiscalyear_close_view.xml",
        "wizard/account_period_create_view.xml",
    ],
    "demo": [],
    "installable": True,
    "application": False,
    "auto_install": False,
    "pre_init_hook": "_pre_init_adopt_types",
    "post_init_hook": "_post_init",
}
