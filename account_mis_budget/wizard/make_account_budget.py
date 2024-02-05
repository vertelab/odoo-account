from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
import dateutil.relativedelta as relativedelta
from datetime import datetime

class AccountClass(models.Model):
    _name = "custom.account.class"
    _description = "A custom account class"

    name = fields.Char()

class make_account_budget(models.TransientModel):
    _name = "make.account.budget.wizard"
    _description = "Make account budget"

    date_type = fields.Many2one('date.range.type', string='Date type', required=True)
    account_ids = fields.Many2many(comodel_name="account.account",string="Accounts",required=True)

    use_last_years_budget = fields.Boolean(string="Use last years budget?")
    
    #account_class = fields.Selection([('intäkter', 'Intäkter'), ('material och varor', 'Material och varor'),('övriga kostnader', 'Övriga konstnader'), ('personalkostnader', 'Personalkostnader'), ('finansiella intäkter/kostnader','Finansiella intäkter/kostnader')], string="Account Class")
    account_class = fields.Many2many(comodel_name='custom.account.class', string='Account class')

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


    #TODO: Maybe use id, instead of a string value of account_class_name, that might modified in the future?
    def get_account_class(self, account_class_name):
        if account_class_name == 'Class 1':
            return ['1']
        elif account_class_name == 'Class 2':
            return ['2']
        elif account_class_name == 'Class 3 & 4':
            return ['3', '4']
        elif account_class_name == 'Class 5':
            return ['5']
        elif account_class_name == 'Class 6':
            return ['6']
        elif account_class_name == 'Class 9':
            return ['9']
        
        #Dessa nedanför ska användas när /data/custom_account_classes.xml använder dessa records.
        """ if account_class_name == 'Intäkter':
            return ['1']
        elif account_class_name == 'Material och varor':
            return ['2']
        elif account_class_name == 'Övriga konstnader':
            return ['3', '4']
        elif account_class_name == 'Personalkostnader':
            return ['5']
        elif account_class_name == 'Finansiella intäkter/kostnader':
            return ['8'] """

    @api.onchange('account_class')
    def _onchange_account_class(self):

        ids = []

        for selected_values in self.account_class:
            for selected_account_class in list(self.get_account_class(selected_values.name)):
                for account in self.env['account.account'].search([]):
                    if str(account.code)[0] == selected_account_class:
                        ids.append(account.id)

        if len(self.account_class) > 0:
            self.write({'account_ids': [(6, 0, ids)]})
        else:
            self.write({'account_ids': [(6, 0, [])]})