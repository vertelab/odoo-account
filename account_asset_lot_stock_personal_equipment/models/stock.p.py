from odoo import api, fields, models, _, exceptions
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


    
class AccountAsset(models.Model):
    _inherit = 'account.asset'
    
    personal_equipment_id = fields.Many2one(
        comodel_name="hr.personal.equipment",
        string="Personal Equipment",
        readonly=True
    )
    
    def action_view_equipment(self):
        return {
            'name': _('Personal Equipment'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.personal.equipment',
            'view_mode': 'list,form',
            'domain': [('id', '=', self.personal_equipment_id.id)]
        }
    
    
    
class PersonalEquipment(models.Model):
    _inherit = 'hr.personal.equipment'

    asset_id = fields.Many2one(
        comodel_name="account.asset",
        string="Asset",
        readonly=True,
    )
    
    def action_view_assets(self):
        return {
            'name': _('It Asset'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.asset',
            'view_mode': 'list,form',
            'domain': [('id', '=', self.asset_id.id)]
        }
   
class StockLot(models.Model):
    _inherit = 'stock.lot'
    
    def _prepare_asset_vals(self, stock_picking, move):
        vals =  super()._prepare_asset_vals(stock_picking, move)
        _logger.warning("Equipment _prepare_asset_vals" * 100)
        if stock_picking.equipment_request_id:
           vals['personal_equipment_id'] = move.personal_equipment_id.id
        return vals
        
    def create_asset(self,vals):
        res =  super().create_asset(vals)
        res.personal_equipment_id.asset_id = res
        return res
        
