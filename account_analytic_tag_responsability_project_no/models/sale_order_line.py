from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"
    authorized_transaction_ids = fields.Many2many('payment.transaction', compute='_compute_authorized_transaction_ids',string='Authorized Transactions', copy=False, readonly=True)

    @api.model
    def create(self, values):
        res = super(SaleOrder, self).create(values)
        for record in res.order_line:
            if record.analytic_tag_ids:
                record._depends_analytic_tag_ids()
        return res

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
         
    def _default_project_tag(self):
        for tag in self.analytic_tag_ids:
            if tag.type_of_tag == "project_number":
               return tag
        return False
    
    def _default_place_tag(self):
        for tag in self.analytic_tag_ids:
            if tag.type_of_tag == "area_of_responsibility":
               return tag
        return False
        
        
    def write(self, values):
        res = super(SaleOrderLine, self).write(values)
        if values.get('analytic_tag_ids'):
            self._depends_analytic_tag_ids()
        return res
            
        
    @api.depends("analytic_tag_ids")
    def _depends_analytic_tag_ids(self):
        for record in self:
            record.project_no = record._default_project_tag()
            record.area_of_responsibility = record._default_place_tag()
                    

    project_no = fields.Many2one(comodel_name='account.analytic.tag', string='Project Analytic Tag', default=_default_project_tag, readonly=True)
    area_of_responsibility= fields.Many2one(comodel_name='account.analytic.tag', string='Place Analytic Tag', default=_default_place_tag, readonly=True)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model
    def create(self, values):
        res = super(SaleOrder, self).create(values)
        for record in res.order_line:
            if record.analytic_tag_ids:
                record._depends_analytic_tag_ids()
        return res

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
         
    def _default_project_tag(self):
        for tag in self.analytic_tag_ids:
            if tag.type_of_tag == "project_number":
               return tag
        return False
    
    def _default_place_tag(self):
        for tag in self.analytic_tag_ids:
            if tag.type_of_tag == "area_of_responsibility":
               return tag
        return False
        
        
    def write(self, values):
        res = super(PurchaseOrderLine, self).write(values)
        if values.get('analytic_tag_ids'):
            self._depends_analytic_tag_ids()
        return res
            
        
    @api.depends("analytic_tag_ids")
    def _depends_analytic_tag_ids(self):
        for record in self:
            record.project_no = record._default_project_tag()
            record.area_of_responsibility = record._default_place_tag()
                    

    project_no = fields.Many2one(comodel_name='account.analytic.tag', string='Project Analytic Tag', default=_default_project_tag, readonly=True)
    area_of_responsibility= fields.Many2one(comodel_name='account.analytic.tag', string='Place Analytic Tag', default=_default_place_tag, readonly=True)
    



