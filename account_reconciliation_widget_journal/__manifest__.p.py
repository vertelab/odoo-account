{
    "name": "Account: Reconciliation Widget Journal Filter",
    "version": "1.0",
    "summary": "Limit which journals and dates the reconcile widget may match against",
    "category": "Accounting",
    "author": "Vertel AB",
    "website": "https://vertel.se/apps/odoo-account/account_reconciliation_widget_journal",
    "license": "AGPL-3",
    "maintainer": "Vertel AB",
    "repository": "https://github.com/vertelab/odoo-account",
    "description": "Adds two settings on the journal: which journals the reconcile widget may match against, and from which date. Useful when a bank journal must not be matched against entries in a closed year, or when only one journal's entries are relevant.\n\nPorted from 14.0. The 14.0 module overrode `_domain_move_lines_for_reconciliation` on `account.reconciliation.widget`, which does not exist in Odoo 18. The filter is applied in the domain of the OCA reconcile widget instead.",
    "depends": ["account", "account_reconcile_oca"],
    "data": ["views/account_journal_view.xml"],
    "installable": True,
    "application": False,
    "auto_install": False
}
