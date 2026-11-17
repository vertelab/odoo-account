from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
import dateutil.relativedelta as relativedelta
from datetime import datetime

_logger = logging.getLogger(__name__)


class AccountMisPeriodWizard(models.TransientModel):
    _name = "account.mis.period.wizard"
    _description = "Helping with creating periods, for report use."

    res_id = fields.Integer('Res ID')

    period = fields.Many2one(comodel_name='account.period', string='Period', required=True)

    def make_report(self):
        mis_report = self.env['mis.report.instance'].browse(self._context.get('active_id'))

        # Odoo 18: account.period has no `code` and no `special` field here —
        # the period is a date.range and carries date_start/date_stop/name.
        first_period = self.env['account.period'].search(
            [], order='date_start asc', limit=1)
        if not first_period:
            raise ValidationError(_("No periods exist. Create a fiscal year first."))

        period_year = self.period.date_start.year
        period_label = self.period.date_start.strftime('%Y/%m')
        manual_date = datetime(year=period_year, month=12, day=31) - relativedelta.relativedelta(years=1)

        mis_report.write({
            "comparison_mode": True,
            "period_ids": [
                (5, 0, 0),
                (0, 0, {
                    'name': _("Ingående balans (%(year)s)", year=manual_date.year),
                    'manual_date_from': first_period.date_start,
                    'manual_date_to': manual_date,
                }),
                (0, 0, {
                    'name': _("Period %(label)s", label=period_label),
                    'manual_date_from': datetime(year=period_year, month=1, day=1),
                    'manual_date_to': self.period.date_stop,
                }),
                (0, 0, {
                    'name': _("Utgående Balans %(label)s", label=period_label),
                    'manual_date_from': first_period.date_start,
                    'manual_date_to': self.period.date_stop,
                }),
            ]
        })
