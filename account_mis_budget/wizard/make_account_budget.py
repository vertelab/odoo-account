from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
import dateutil.relativedelta as relativedelta
from datetime import datetime

_logger = logging.getLogger(__name__)

class MisBudgetAccount(models.Model):
    _inherit = "mis.budget.by.account"

    def action_create_income_budget(self):
        
        dr = self.env['date.range.type'].search([('name','like','%mon%')])
        if len(dr) == 0:
            dr = self.env['date.range.type'].search([])
       
        wizard_id = self.env['make.account.budget.wizard'].create({
            'budget_id': self.id,
            'date_type': dr[0].id,
            })
        return self.env.ref('account_mis_budget.action_make_account_budget').with_context({'res_id': wizard_id.id}).read()[0]
       
    

class AccountClass(models.Model):
    _name = "custom.account.class"
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
    _name = "make.account.budget.wizard"
    _description = "Make account budget"

    date_type = fields.Many2one('date.range.type', string='Date type', required=True)
    account_ids = fields.Many2many(comodel_name="account.account",string="Accounts",required=True)
    budget_id = fields.Many2one(comodel_name="mis.budget.by.account", default=lambda b: b.env.context.get('active_id'))

    use_last_years_budget = fields.Boolean(string="Use accounts from last year?", help="If checked in we create lines only for accounts that were used in an account.move.line last year")
    
    #account_class = fields.Selection([('intäkter', 'Intäkter'), ('material och varor', 'Material och varor'),('övriga kostnader', 'Övriga konstnader'), ('personalkostnader', 'Personalkostnader'), ('finansiella intäkter/kostnader','Finansiella intäkter/kostnader')], string="Account Class")
    account_class_ids = fields.Many2many(comodel_name='custom.account.class', string='Account class')

    def make_report(self):
        
        budget_account_id = self.env['mis.budget.by.account'].browse(self._context.get('active_id'))

        for account in self.account_ids:
            for date_range in self.date_type.date_range_ids:
            #    env['mis.budget.kpi.item'].create({
                if date_range.date_start > budget_account_id.date_to:
                    break
                if not self.env['mis.budget.by.account.item'].search([('budget_id','=',budget_account_id.id),
                                                       ('date_range_id','=',date_range.id),
                                                       ('date_from','=',date_range.date_start),
                                                       ('date_to','=',date_range.date_end),
                                                       ('account_id','=',account.id)]):

                    if self.env['account.move.line'].search([('account_id','=',account.id), 
                                                             ('date', '>=', datetime(year=date_range.date_end.year, month=1, day=1) - relativedelta.relativedelta(years=1)),
                                                             ('date', '<=', datetime(year=date_range.date_end.year, month=12, day=31) - relativedelta.relativedelta(years=1))]) and self.use_last_years_budget:
                        self.env['mis.budget.by.account.item'].create({
                            'budget_id': budget_account_id.id, 
                            'date_range_id': date_range.id, 
                            'date_from': date_range.date_start, 
                            'date_to': date_range.date_end, 
                            'account_id': account.id,
                        })
                    elif not self.use_last_years_budget:
                        self.env['mis.budget.by.account.item'].create({
                            'budget_id': budget_account_id.id, 
                            'date_range_id': date_range.id, 
                            'date_from': date_range.date_start, 
                            'date_to': date_range.date_end, 
                            'account_id': account.id,
                        })

    @api.onchange('budget_id','account_class_ids')
    def _onchange_budget_account(self):
        _logger.warning(f"{self.env.context=}")
        self.budget_id = self.env['mis.budget.by.account'].browse(self.env.context.get('active_id'))
    
    @api.onchange('account_class_ids')
    def _onchange_account_class(self):
        ids = []
        for account_id in self.account_class_ids.get_account_class(self.use_last_years_budget):
            ids.append(account_id)    
        self.write({'account_ids': [(6, 0, ids)]})
