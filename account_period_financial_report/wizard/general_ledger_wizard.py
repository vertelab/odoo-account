from odoo import _, api, fields, models
from odoo.exceptions import UserError
import logging
import time

_logger = logging.getLogger(__name__)

class ReplaceBaseFiscal(models.TransientModel):
    _inherit = 'general.ledger.report.wizard'

    def _init_date_from(self):
        today = fields.Date.context_today(self)

        period = self.env['account.period'].date2period(today)
        if len(period) != 0:
            _logger.warning(f"{period=}")
            return period[0].fiscalyear_id.date_start


    @api.depends("date_from")
    def _compute_fy_start_date(self):
        for wiz in self:
            if wiz.date_from:
                wiz.fy_start_date = self.date_from
            else:
                wiz.fy_start_date = False