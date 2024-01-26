from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

class make_account_budget(models.TransientModel):
    _name = "make.account.budget.wizard"
    _description = "Make account budget"

    date_type = fields.Many2one('date.range.type', string='Date type', required=True)
    account_ids = fields.Many2many(comodel_name="account.account",string="Accounts",required=True)

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
                    self.env['mis.budget.by.account.item'].create({
                            'budget_id': budget_account_id.id, 
                            'date_range_id': date_range.id, 
                            'date_from': date_range.date_start, 
                            'date_to': date_range.date_end, 
                            'account_id': account.id,
                        })
