import logging
from odoo import api, fields, models, _, exceptions

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    period_id = fields.Many2one('account.period', string='Period', related='move_id.period_id', store=True,
                                readonly=True)
    fiscalyear_id = fields.Many2one(comodel_name='account.fiscalyear', related='move_id.period_id.fiscalyear_id',
                                    store=True, readonly=True)

    def reconcile(self):
        res = super(AccountMoveLine, self).reconcile()
        # 19.0 removed account.full.reconcile.exchange_move_id. The exchange
        # move is now reachable from the reconciled lines themselves.
        if res and 'full_reconcile' in res:
            for exchange_move in res['full_reconcile'].reconciled_line_ids.exchange_move_ids:
                period_id = self.env['account.period'].date2period(exchange_move.date)
                exchange_move.period_id = period_id.id
        return res
