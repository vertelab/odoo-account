from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
import dateutil.relativedelta as relativedelta
from datetime import datetime

_logger = logging.getLogger(__name__)

class MisBudgetAccount(models.Model):
    _inherit = "mis.budget.by.account"
    
    date_type = fields.Many2one('date.range.type', string='Date type', required=True)
    
    def make_account_forecast(self):
        dr = self.env['date.range.type'].search([('name','like','%mon%')])
        if len(dr) == 0:
            dr = self.env['date.range.type'].search([])
        wizard_id = self.env['make.account.budget.wizard'].create({
            'budget_id': self.id,
            })
        return self.env.ref('account_mis_budget.action_make_account_forecast').with_context({'res_id': wizard_id.id}).read()[0]

class AccountClass(models.Model):
    _name = "custom.account.forecast"
    _description = "A custom account class"

    name = fields.Char()
    account_class = fields.Char(string="Account Class",help="Coma separated list of beginning of account code for account classes eg 5,6")
    
      #TODO: Maybe use id, instead of a string value of account_class_name, that might modified in the future?
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

class make_account_budget(models.TransientModel):
    _name = "make.account.forecast.wizard"
    _description = "Make account budget"

    account_ids = fields.Many2many(comodel_name="account.account",string="Accounts",required=True)
    budget_id = fields.Many2one(comodel_name="mis.budget.by.account", default=lambda b: b.env.context.get('active_id'))

    use_account_from_year = fields.Boolean(string="Use accounts period?", help="If checked in we create lines only for accounts that were used in an account.move.line during period")
    use_contract = fields.Boolean(string="Use contracts for forecast?", help="If checked in we use contracts during period, if and for other account we are using budget")
    use_first_period = fields.Boolean(string="Distribute first period linear", help="If checked in we use first period and distribute during the whole period")
    
    account_class_ids = fields.Many2many(comodel_name='custom.account.forecast', string='Account class')
    percentage_factor = fields.Float(string='Percentage Factor')
    
    
    def make_report(self):
        for account in self.account_ids:
            for date_range in self.budget_id.date_type.date_range_ids:
                if (date_range.date_start >= self.budget_id.date_from) and (date_range.date_end <= self.budget_id.date_to):                
                    budget_item = self.env['mis.budget.by.account.item'].search([('budget_id','=',self.budget_id.id),
                                                           ('date_range_id','=',date_range.id),
                                                           ('date_from','=',date_range.date_start),
                                                           ('date_to','=',date_range.date_end),
                                                           ('account_id','=',account.id)])
                                                           
                    if not budget_item: # Do not overwrite a current budget item
                        budget_item = self.env['mis.budget.by.account.item'].create({
                                'name': account.name,
                                'budget_id': self.budget_id.id, 
                                'date_range_id': date_range.id, 
                                'date_from': date_range.date_start, 
                                'date_to': date_range.date_end, 
                                'account_id': account.id,
                            })
                        if self.use_account_from_year: # Use historic data for the budget
                            balance = sum(self.env['account.move.line'].search([
                                ('account_id','=',account.id),('move_id.state','=','posted'),
                                ('date','>=',date_range.date_start - relativedelta.relativedelta(years=1)),
                                ('date','<=',date_range.date_end - relativedelta.relativedelta(years=1))]).mapped('balance'))
                            if balance > 0:
                                budget_item.write({'debit':abs(balance) * self.percentage_factor})
                            else:
                                budget_item.write({'credit':abs(balance) * self.percentage_factor})

    @api.onchange('budget_id','account_class_ids','use_account_from_year')
    def _onchange_budget_account(self):
        _logger.warning(f"{self.env.context=}")
        #self.budget_id = self.env['mis.budget.by.account'].browse(self.env.context.get('active_id'))
    
    @api.onchange('account_class_ids')
    def _onchange_account_class(self):
        self.write({'account_ids': [(6, 0, self.account_class_ids.get_account_class(self.use_account_from_year))]})
