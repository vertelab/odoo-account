"""Journal and date filters for the OCA reconcile widget.

Odoo 18 has no `account.reconciliation.widget`: the widget is
`account_reconcile_oca`, and the candidate journal items it offers come from
the `domain` of `add_account_move_line_id` in its views. There is no Python
hook that builds that domain, so filtering is done through the domain itself.

This module adds two settings on `account.journal` — which journals may be
matched against, and from which date — and exposes them as computed fields on
`account.bank.statement.line` so the widget's view domain can reference them.

The 14.0 module overrode `_domain_move_lines_for_reconciliation` on the old
widget; that method is gone. The account-level reconcile view
(`account.account.reconcile`) is an SQL view with no journal, so the filter
applies to bank statement reconciliation only.
"""

from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    allowed_reconcile_journal_ids = fields.Many2many(
        'account.journal',
        'account_journal_reconciliation_rel',
        'col1', 'col2',
        string="Journal filter for reconcile widget",
        help="Keep empty to allow all journals",
    )
    after_allowed_reconcile_date = fields.Date(
        string="After date filter for reconcile widget",
        help="Keep empty to allow all dates",
    )


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    reconcile_filter_journal_ids = fields.Many2many(
        "account.journal",
        "account_bank_statement_line_reconcile_journal_rel",
        "statement_line_id", "journal_id",
        string="Reconcile: allowed journals",
        compute="_compute_reconcile_filters",
    )
    reconcile_filter_after_date = fields.Date(
        string="Reconcile: after date",
        compute="_compute_reconcile_filters",
    )

    @api.depends("journal_id")
    def _compute_reconcile_filters(self):
        for record in self:
            journal = record.journal_id
            record.reconcile_filter_journal_ids = journal.allowed_reconcile_journal_ids
            record.reconcile_filter_after_date = journal.after_allowed_reconcile_date
