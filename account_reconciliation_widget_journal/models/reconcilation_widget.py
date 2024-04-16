import copy

from psycopg2 import sql

from datetime import datetime, date, time, timezone
from odoo import _, api, models, fields
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.misc import format_date, formatLang, parse_date


class AccountJournal(models.Model):
    _inherit = "account.journal"

    allowed_reconcile_journal_ids = fields.Many2many('account.journal', 'account_journal_reconciliation_rel',
                                                     'col1', 'col2',
                                                     string="Journal filter for reconcile widget",
                                                     help="Keep empty to allow all journals")
    after_allowed_reconcile_date = fields.Date(string="After date filter for reconcile widget",
                                               help="Keep empty to allow all dates")


class AccountReconciliation(models.AbstractModel):
    _inherit = "account.reconciliation.widget"

    @api.model
    def _domain_move_lines_for_reconciliation(
            self,
            st_line,
            aml_accounts,
            partner_id,
            excluded_ids=None,
            search_str=False,
            mode="rp",
    ):
        domain = super(AccountReconciliation, self)._domain_move_lines_for_reconciliation(
            st_line, aml_accounts, partner_id, excluded_ids, search_str, mode
        )
        domain = expression.AND([domain, [("move_id", "!=", st_line.move_id.id)]])
        if st_line.journal_id.after_allowed_reconcile_date:
            domain = expression.AND(
                [domain, [("move_id.date", ">=", st_line.journal_id.after_allowed_reconcile_date)]])
        if st_line.journal_id.allowed_reconcile_journal_ids:
            domain = expression.AND(
                [domain, [("move_id.journal_id", "in", st_line.journal_id.allowed_reconcile_journal_ids.ids)]])

        return domain
