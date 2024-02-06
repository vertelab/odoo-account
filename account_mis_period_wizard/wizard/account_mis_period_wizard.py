from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
import dateutil.relativedelta as relativedelta
from datetime import datetime

class account_mis_period_wizard(models.TransientModel):
      _name = "account.mis.period.wizard"
      _description = "Helping with creating periods, for report use."

      period = fields.Many2one(comodel_name='account.period', string='Period')

      def make_report(self):
            logging.warning('make_report')
            mis_report = self.env['mis.report.instance'].browse(self._context.get('active_id'))

            #TODO: Get the first fiscal year possible in the model account.period
            fiscal_years = self.env['account.period'].search([('special', '=', False)]) #There is an extra element called "Opening Period YYYY" that we dont want

            #logging.warning(fiscal_years.date_start)
            #logging.warning(sorted(fiscal_years.date_start))

            #for x in fiscal_years:
            #     logging.warning(x.date_start)

            #logging.warning("\n\n\n")

            sorted_fiscal_years = fiscal_years.sorted(lambda period: period.date_start)

            #for y in sorted_fiscal_years:
                  #logging.warning(y.date_start)

            #TODO : Sort the fiscal year

            mis_report.write({"comparison_mode":True,
                  "period_ids":[(5, 0, 0),
                  (0,0,{'name': f'Ingående balans ({(datetime(year=self.period.date_start.year, month=12, day=31) - relativedelta.relativedelta(years=1)).year})',
                  'manual_date_from': sorted_fiscal_years[0].date_start,
                  'manual_date_to': datetime(year=self.period.date_start.year, month=12, day=31) - relativedelta.relativedelta(years=1)}),  #TODO: Perhaps you want to have up until period month
                  (0,0,{'name': f'Period {datetime.strptime(self.period.code, "%m/%Y").strftime("%Y/%m")}', # adjusted the string from 'Period MM/YYYY' to a 'YYYY/MM' string instead
                  'manual_date_from': datetime(year=self.period.date_start.year, month=1, day=1), 
                  'manual_date_to': self.period.date_stop}),
                  (0,0,{'name': f'Utgående Balans ({datetime.strptime(self.period.code, "%m/%Y").strftime("%Y/%m")})',
                  'manual_date_from': sorted_fiscal_years[0].date_start,
                  'manual_date_to': self.period.date_stop})
                  ]
                  })

