import logging
from odoo import api, fields, models, _, exceptions

_logger = logging.getLogger(__name__)

class AccountAccount(models.Model):
    _inherit = 'account.account'
    
    

    def get_debit_credit_balance(self, period, target_move):
        self.ensure_one()
        if not target_move or target_move == 'all':
            target_move = ['draft', 'posted']
        else:
            target_move = [target_move]
        lines = self.env['account.move.line'].search(
            [('move_id.period_id', '=', period.id), ('account_id', '=', self.id),
             ('move_id.state', 'in', target_move)])  # move lines with period_id
        return {
            'debit': sum(lines.mapped('debit')),
            'credit': sum(lines.mapped('credit')),
            'balance': sum(lines.mapped('debit')) - sum(lines.mapped('credit')),
        }

    def get_balance(self, period, target_move):
        self.ensure_one()
        return self.get_debit_credit_balance(period, target_move).get('balance')

    def sum_period(self):
        self.ensure_one()

        domain = [('move_id.period_id', 'in',
                   self.env['account.period'].get_period_ids(self._context.get('period_start'),
                                                             self._context.get('period_stop',
                                                                               self._context.get('period_start')))),
                  ('account_id', '=', self.id)]

        if self._context.get('target_move') in ['draft', 'posted']:
            domain.append(('move_id.state', '=', self._context.get('target_move')))

        return sum([a.balance for a in self.env['account.move.line'].search(domain)])
