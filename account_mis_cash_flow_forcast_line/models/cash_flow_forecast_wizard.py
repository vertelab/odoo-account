from odoo import models, fields, api
import dateutil.relativedelta as relativedelta
import logging

_logger = logging.getLogger(__name__)


class AccountasdClass(models.Model):

    _name = "cash.flow.custom.account.class"
    _description = "A custom account class"

    name = fields.Char()
    account_class = fields.Char(string="Account Class",help="Coma separated list of beginning of account code for account classes eg 5,6")
       

    def get_account_class(self, use_account_from_year):
        account_ids = []
        for ac in self:
            for ac_begin in [str(code) for code in ac.account_class.split(',') if len(ac.account_class) > 0]:
                _logger.warning(f"{ac_begin}   ^{ac_begin}")
                for account in self.env['account.account'].search([('code', 'like', f"{ac_begin}___"),]):
                    if use_account_from_year:
                        nbr_use = self.env['account.move.line'].search_count(['&',
                                ('date','>=', fields.Date.today() - relativedelta.relativedelta(years=1)),
                                ('account_id', '=', account.id),
                            ])
                        if nbr_use > 0:
                            account_ids.append(account.id)
                    else:
                        account_ids.append(account.id)
        return account_ids


class Cash_Flow_Forecast_Wizard(models.TransientModel):

    _name = 'cash.flow.forecast.wizard'
    _description = 'Creates a forecast from 3 months old data'

    account_ids = fields.Many2many(comodel_name="account.account",string="Accounts",required=True)
    budget_id = fields.Many2one("mis.budget.by.account")

    use_account_from_year = fields.Boolean(string="Use accounts from last year?", help="If checked in we create lines only for accounts that were used in an account.move.line last year")
    
    account_class_ids = fields.Many2many(comodel_name='cash.flow.custom.account.class', string='Account class')
    percentage_factor = fields.Float(string='Percentage Factor')
    

    def get_dates(self, back_range):

        today = fields.Date.today()

        delta = relativedelta.relativedelta

        start_date = fields.date(today.year,today.month,1) - delta(months=back_range)

        end_date = fields.date(today.year,today.month,1) - delta(days=1)

        return {"start_date": start_date, "end_date": end_date}


    def get_forecast_factor(self, account, back_range, dates):

        balance_average = sum(self.env['account.move.line'].search([
            ('account_id','=',account.id),('move_id.state','=','posted'),
            ('date','>=',dates["start_date"]),
            ('date','<=',dates["end_date"])]).mapped('balance')) / back_range

        budget_balance_average = sum(self.env['mis.budget.by.account.item'].search([
            ('account_id','=',account.id),('date','>=',dates['start_date']),
            ('date','<=',dates['end_date'])]).mapped('balance')) / back_range

        forecast_factor = budget_balance_average / balance_average

        return forecast_factor


            

    def create_forecast(self,account,forecast_factor):

        budget_dates = self.get_date_range_from_budget()

        for date in budget_dates:

            budget_balance = self.env['mis.budget.by.account.item'].search([
                ('account_id','=',account.id),('date','>=',date.start_date),
                ('date','<=',date.end_date)]).mapped('balance')
            
            adjusted_budget_balance = budget_balance * forecast_factor

            self.env['mis.cash_flow.forecast_line'].create({
                    'name': account.name,
                    'date': date.start_date, 
                    'account_id': account.id,
                    'balance': budget_balance,
                    'adjusted_balance': adjusted_budget_balance,
                    'forecast_factor': forecast_factor
                })


    def get_date_range_from_budget(self):

        budget_start_date = self.budget_id.date_start

        budget_end_date = self.budget_id.end_date

        for date in self.budget_id.date_type.date_range_ids:
            
            if date.date_start >= budget_start_date and date.end_date <= budget_end_date:

                yield date


    def action_make_forecast(self):
        
        back_range = 3

        dates = self.get_dates(back_range)

        for account in self.account_ids:

            forecast_factor = self.get_forecast_factor(account,back_range,dates)

            self.create_forecast(account,forecast_factor)


            


    # def get_budget_factor(self, account):

    #     for dates in previous_dates:                                            

    #         budget_balance = sum(self.env['mis.budget.by.account.item'].search([
    #             ('account_id','=',account.id),('date','>=',dates[',start_date']),
    #             ('date','<=',dates['end_date'])]).mapped('balance'))
            
    #     return budget_balance


    @api.onchange('account_class_ids')
    def _onchange_account_class(self):
        self.write({'account_ids': [(6, 0, self.account_class_ids.get_account_class(self.use_account_from_year))]})
