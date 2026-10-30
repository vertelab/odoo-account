{
    "name": "Account: Fiscal Year",
    "version": "18.0.1.1.0",
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
- Swedish date range types via bridge module (l10n_se_account_fiscal_year)
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
        "security/ir.model.access.csv",
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
    "post_init_hook": "_migrate_from_account_period_vrtl",
}
