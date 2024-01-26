from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

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
            lines = self.env['account.move.line'].search([('account_id','=',record.account_id.id),('move_id.state','=','posted'),('date','>=',record.date_from-dateutil.relativedelta.relativedelta(years=1)),('date','<=',record.date_to-dateutil.relativedelta.relativedelta(years=1))])
            logging.warning(record)

            balance = sum(lines.mapped('balance'))

            if balance > 0:
                record.write({'debit':abs(balance)})
            else:
                record.write({'credit':abs(balance)})

        # loop through them, and modify them by the percentage factor

        # update the view???
