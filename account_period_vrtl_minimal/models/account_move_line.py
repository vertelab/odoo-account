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
        if res and 'full_reconcile' in res and res['full_reconcile'].exchange_move_id:
            exchange_move_id = res['full_reconcile'].exchange_move_id
            period_id = self.env['account.period'].date2period(exchange_move_id.date)
            exchange_move_id.period_id = period_id.id
        return res
