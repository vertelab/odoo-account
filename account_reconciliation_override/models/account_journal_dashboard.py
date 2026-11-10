from odoo import models, api, _, fields

class account_journal(models.Model):
    _inherit = "account.journal"

    def get_journal_dashboard_datas(self):
        res = super(account_journal, self).get_journal_dashboard_datas()

        self._cr.execute('''
                SELECT COUNT(st_line.id)
                FROM account_bank_statement_line st_line
                JOIN account_move st_line_move ON st_line_move.id = st_line.move_id
                JOIN account_bank_statement st ON st_line.statement_id = st.id
                WHERE st_line_move.journal_id IN %s
                AND st.state = 'open'
                AND NOT st_line.is_reconciled
            ''', [tuple(self.ids)])
        
        res['number_to_reconcile'] = self.env.cr.fetchone()[0]

        return res