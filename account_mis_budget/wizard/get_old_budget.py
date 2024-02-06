from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
import dateutil.relativedelta as relativedelta

class get_old_budget(models.TransientModel):
    _name = "get.old.budget.wizard"
    _description = "Retrieving the past budgets"
    
    #date_type = fields.Many2one('date.range.type', string='Date type', required=True) # Month, Weeks, Every two weeks
    percentage_factor = fields.Float(string="Percentage Factor")

    def modify_budget(self):
        active_ids = self._context.get('active_ids', [])

        # Log the value of active_ids to debug
        logging.warning(f'active_ids: {active_ids}')

        # Use the active_ids to retrieve the selected records
        selected_records = self.env['mis.budget.by.account.item'].browse(active_ids)

         #Log the selected records
        for record in selected_records:
            lines = self.env['account.move.line'].search([('account_id','=',record.account_id.id),('move_id.state','=','posted'),('date','>=',record.date_from - relativedelta.relativedelta(years=1)),('date','<=',record.date_to - relativedelta.relativedelta(years=1))])

            balance = sum(lines.mapped('balance'))
            logging.warning(balance)

            if balance > 0:
                record.write({'debit':abs(balance) * self.percentage_factor})
            else:
                record.write({'credit':abs(balance) * self.percentage_factor})
