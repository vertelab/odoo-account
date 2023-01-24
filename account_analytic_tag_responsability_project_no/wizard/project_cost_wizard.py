from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


class ProjectAndCostCenter(models.TransientModel):
    _name = 'project.cost.center.wizard'

    res_id = fields.Char(string="Record ID")

    res_model = fields.Char(string="Record Model")

    project_no = fields.Many2one(comodel_name='account.analytic.tag', string='Project', readonly=False,
                                 domain="[('type_of_tag', '=', 'project_number')]")

    area_of_responsibility = fields.Many2one(comodel_name='account.analytic.tag', string='Cost Center',
                                             readonly=False, domain="[('type_of_tag', '=', 'area_of_responsibility')]")

    def action_add_project_and_cost_center(self):
        rec_id = self.env[self.res_model].browse(int(self.res_id))
        print(self.res_model)
        if self.res_model in ['sale.order', 'purchase.order']:
            for line in rec_id.order_line:
                line.write({'project_no': self.project_no.id, 'area_of_responsibility': self.area_of_responsibility.id})
        elif self.res_model == 'account.move':
            for line in rec_id.invoice_line_ids:
                line.write({'project_no': self.project_no.id, 'area_of_responsibility': self.area_of_responsibility.id})
