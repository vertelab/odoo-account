import logging
from odoo import api, fields, models, _, exceptions

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    period_id = fields.Many2one('account.period', string='Period', related='move_id.period_id', store=True,
                                readonly=True)
    fiscalyear_id = fields.Many2one(comodel_name='account.fiscalyear', related='move_id.period_id.fiscalyear_id',
                                    store=True, readonly=True)
    latest_payment_date = fields.Date(
        store=True, string='Invoice Payment Date', related='move_id.payment_date',
    )
