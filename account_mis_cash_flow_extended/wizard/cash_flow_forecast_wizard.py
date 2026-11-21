from odoo import models, fields, api
from odoo.exceptions import UserError
import dateutil.relativedelta as relativedelta
import logging

_logger = logging.getLogger(__name__)


class CashFlowForecastWizard(models.TransientModel):

    _name = 'cash.flow.forecast.wizard'
    _description = 'Creates a forecast from 3 months old data'

    account_ids = fields.Many2many(comodel_name="account.account",string="Accounts",required=True)
    budget_id = fields.Many2one("mis.budget.by.account")
    
    account_class_ids = fields.Many2many(comodel_name='cash.flow.custom.account.class', string='Account class')
    
    summed_budget_balance = fields.Float(string="The Sum of the Budget Balance")
    summed_result_balance = fields.Float(string="The Sum of the Result Balance")
    budget_balance_average = fields.Float(string="The Average budget Balance")
    result_balance_average = fields.Float(string="The Average Result Balance")


    def action_make_forecast(self):
        
        self.remove_previous_forecasts()

        back_range = 3

        dates = self.get_dates(back_range)

        for account in self.account_ids:

            forecast_factor = self.get_forecast_factor(account,back_range,dates)

            self.create_forecast(account,forecast_factor)

        return {
                'name': ('Cash Flow Forecast Line'),
                'res_model': 'mis.cash_flow.forecast_line',
                'view_mode': 'tree',
                'target': 'current',
                'type': 'ir.actions.act_window',
            }


    def remove_previous_forecasts(self):

        self.env["mis.cash_flow.forecast_line"].search([]).unlink()


    def get_dates(self, back_range):

        today = fields.Date.today()

        delta = relativedelta.relativedelta

        start_date = fields.date(today.year,today.month,1) - delta(months=back_range)

        end_date = fields.date(today.year,today.month,1) - delta(days=1)
        
        if start_date.year != today.year:

            start_date = fields.date(today.year,1,1)

            if end_date.year != today.year:

                end_date = fields.date(today.year,today.month,1) + delta(months=1) - delta(days=1)

        return {"start_date": start_date, "end_date": end_date}


    def get_forecast_factor(self, account, back_range, dates):

        balance = sum(self.env['account.move.line'].search([
            ('account_id','=',account.id),('move_id.state','=','posted'),
            ('date','>=',dates["start_date"]),
            ('date','<=',dates["end_date"])]).mapped('balance'))

        budget_balance = sum(self.env['mis.budget.by.account.item'].search([
            ('account_id','=',account.id),('date','>=',dates['start_date']),
            ('date','<=',dates['end_date']),('budget_id','=',self.budget_id.id)]).mapped('balance'))

        balance_average = balance / back_range
        budget_balance_average = budget_balance / back_range

        self.summed_result_balance = balance
        self.result_balance_average = balance_average
        self.summed_budget_balance = budget_balance
        self.budget_balance_average = budget_balance_average

        if budget_balance_average == 0:

            return 1

        forecast_factor = balance_average / budget_balance_average

        return forecast_factor


    def create_forecast(self,account,forecast_factor):

        budget_dates = self.get_date_range_from_budget()

        for date in budget_dates:

            budget_balance = sum(self.env['mis.budget.by.account.item'].search([
                ('account_id','=',account.id),('date','>=',date.date_start),
                ('date','<=',date.date_end),('budget_id','=',self.budget_id.id)]).mapped('balance'))
            
            adjusted_budget_balance = budget_balance * forecast_factor

            self.env['mis.cash_flow.forecast_line'].create({
                    'name': account.name,
                    'date': date.date_start, 
                    'account_id': account.id,
                    'balance': budget_balance,
                    'adjusted_balance': adjusted_budget_balance,
                    'forecast_factor': forecast_factor,
                    'summed_result_balance': self.summed_result_balance,
                    'result_balance_average': self.result_balance_average,
                    'summed_budget_balance': self.summed_budget_balance,
                    'budget_balance_average': self.budget_balance_average
                })


    def get_date_range_from_budget(self):

        budget_start_date = self.budget_id.date_from

        budget_end_date = self.budget_id.date_to

        for date in self.budget_id.date_type.date_range_ids:
            
            if date.date_start >= budget_start_date and date.date_end <= budget_end_date:

                yield date


    @api.onchange('account_class_ids')
    def _onchange_account_class(self):
        self.write({'account_ids': [(6, 0, self.account_class_ids.get_account_class())]})


class AccountClass(models.Model):

    _name = "cash.flow.custom.account.class"
    _description = "A custom account class"

    name = fields.Char()
    account_class = fields.Char(string="Account Class",help="Coma separated list of beginning of account code for account classes eg 5,6")
       

    def get_account_class(self):

        account_ids = []
        for ac in self:
            for ac_begin in [str(code) for code in ac.account_class.split(',') if len(ac.account_class) > 0]:
                _logger.warning(f"{ac_begin}   ^{ac_begin}")
                for account in self.env['account.account'].search([('code', 'like', f"{ac_begin}___"),]):
                    nbr_use = self.env['account.move.line'].search_count(['&',
                            ('date','>=', fields.Date.today() - relativedelta.relativedelta(years=1)),
                            ('account_id', '=', account.id),
                        ])
                    if nbr_use > 0:
                        account_ids.append(account.id)

        return account_ids


   
