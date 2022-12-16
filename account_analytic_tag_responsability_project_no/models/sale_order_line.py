from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang, get_lang

import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    project_no = fields.Many2one(comodel_name='account.analytic.tag', string='Project', readonly=False,
                                 domain="[('type_of_tag', '=', 'project_number')]")
    area_of_responsibility = fields.Many2one(comodel_name='account.analytic.tag', string='Cost Center',
                                             readonly=False, domain="[('type_of_tag', '=', 'area_of_responsibility')]")
                                                                                        
    
    @api.onchange('product_id')
    def product_id_change(self):
        vals = super().product_id_change()
        if not self.product_id:
            return
            
        if self.product_id.categ_id:
            self.project_no = self.product_id.categ_id.project_no
        else:
            self.project_no = False
            
        if self.product_id.categ_id:
            self.area_of_responsibility = self.product_id.categ_id.area_of_responsibility
        else:
            self.area_of_responsibility = False
            
        return vals

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    project_no = fields.Many2one(comodel_name='account.analytic.tag', string='Project', readonly=False,
                                 domain="[('type_of_tag', '=', 'project_number')]")
    area_of_responsibility = fields.Many2one(comodel_name='account.analytic.tag', string='Cost Center',
                                             readonly=False, domain="[('type_of_tag', '=', 'area_of_responsibility')]")
    
    def _product_id_change(self):
        vals = super()._product_id_change()
        if not self.product_id:
            return
        if self.product_id.categ_id:
            self.project_no = self.product_id.categ_id.project_no
        else:
            self.project_no = False
            
        if self.product_id.categ_id:
            self.area_of_responsibility = self.product_id.categ_id.area_of_responsibility
        else:
            self.area_of_responsibility = False   
            
        return vals

        
        
