from odoo import api, fields, models, _, exceptions
import logging
_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    def reconcile(self):

        res = super(AccountMoveLine, self).reconcile()
        if res and 'full_reconcile' in res and res['full_reconcile'].exchange_move_id:
            exchange_move_id = res['full_reconcile'].exchange_move_id
            period_id = self.env['account.period'].date2period(exchange_move_id.date)
            exchange_move_id.period_id = period_id.id
        return res
