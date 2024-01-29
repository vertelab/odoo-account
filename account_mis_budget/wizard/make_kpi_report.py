from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

class make_kpi_report(models.TransientModel):
    _name = "make.kpi.report.wizard"
    _description = "Make a kpi report"
    
    date_type = fields.Many2one('date.range.type', string='Date type', required=True) # Month, Weeks, Every two weeks

    def make_report(self):
        
        budget_kpi_id = self.env['mis.budget'].browse(self._context.get('active_id'))

        for kpi in budget_kpi_id.report_id.all_kpi_ids:
            for date_range in self.date_type.date_range_ids:
                #logging.warning(date_range.name)

                if date_range.date_start > budget_kpi_id.date_to:
                    break
                if not self.env['mis.budget.item'].search([('budget_id','=',budget_kpi_id.id), 
                                                       ('report_id','=',budget_kpi_id.report_id.id),
                                                       ('date_range_id','=',date_range.id),
                                                       ('date_from','=',date_range.date_start),
                                                       ('date_to','=',date_range.date_end),
                                                       ('kpi_expression_id','=',kpi.id)]):
                    self.env['mis.budget.item'].create({
                            'budget_id': budget_kpi_id.id, 
                            'report_id': budget_kpi_id.report_id,
                            'date_range_id': date_range.id, 
                            'date_from': date_range.date_start, 
                            'date_to': date_range.date_end, 
                            'kpi_expression_id': kpi.id,
                        })
