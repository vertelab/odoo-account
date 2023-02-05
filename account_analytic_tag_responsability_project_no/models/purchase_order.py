from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        if len(self.order_line.filtered(lambda line: not line.area_of_responsibility and not line.display_type)) > 0:
            raise ValidationError(_("Kindly select a Cost Center tag for all line items"))
        res = super(PurchaseOrder, self).button_confirm()
        return res
        
    def action_create_invoice(self):
        vals = super().action_create_invoice()
        
        for order in self:
            for invoice in order.invoice_ids:
                for line in invoice.line_ids:
                    if line.purchase_line_id:
                            line.project_no = line.purchase_line_id.project_no
                            line.area_of_responsibility = line.purchase_line_id.area_of_responsibility
        
        return vals

    def action_add_project_and_cost_center_wizard(self):
        view_id = self.env.ref(
            'account_analytic_tag_responsability_project_no.choose_project_number_and_cost_center_view_form').id

        name = _('Add Project and Cost Center to Purchase Order Lines')

        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'project.cost.center.wizard',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': {
                'default_res_id': self.id,
                'default_res_model': self._name,
            }
        }
