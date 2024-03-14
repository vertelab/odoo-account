from odoo import api, fields, models, _, exceptions
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class StockLocation(models.Model):
    _inherit = "stock.location"
    res_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Owner",
    )#???
    


class StockLot(models.Model):
    _inherit = 'stock.lot'
    
    asset_profile_id = fields.Many2one(
        comodel_name="account.asset.profile",
        string="Asset Profile",
        #compute="_compute_asset_profile",
        store=True,
        readonly=False,
    )
    
    asset_id = fields.Many2one(
        comodel_name="account.asset",
        string="Asset",
        ondelete="restrict",
        check_company=True,
    )
    
    def _prepare_asset_vals(self, stock_picking, move):
        depreciation_base = move.purchase_line_id.price_unit
        owner = False
        
        stock_picking.location_dest_id.company_id.partner_id.id if stock_picking.picking_type_code == "incoming" else stock_picking.partner_id.id,
        
        if stock_picking.picking_type_code == "incoming" and stock_picking.location_dest_id.res_partner_id:
           owner = stock_picking.location_dest_id.res_partner_id.id
        elif stock_picking.picking_type_code == "incoming" and stock_picking.location_dest_id.company_id.partner_id:
            owner = stock_picking.location_dest_id.company_id.partner_id.id
        else:
            owner = stock_picking.partner_id.id
        
        vals = {
            "name": self.name,
            "profile_id": self.asset_profile_id.id if self.asset_profile_id else move.asset_profile_id.id,
            "purchase_value": depreciation_base,
            "partner_id": owner,
            "date_start": stock_picking.date,
        }
        #raise UserError(str(vals))
        return vals
    
    def create_asset(self,vals):
        self.asset_id = self.env['account.asset'].create(vals)
        return self.asset_id
        
    def update_partner_asset(self,partner_id):
        self.asset_id.partner_id = partner_id
        

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    asset_profile_id = fields.Many2one(
        comodel_name="account.asset.profile",
        string="Asset Profile",
        #compute="_compute_asset_profile",
        store=True,
        readonly=False,
    )


class StockMove(models.Model):
    _inherit = 'stock.move'
    asset_profile_id = fields.Many2one(
        comodel_name="account.asset.profile",
        string="Asset Profile",
        compute="_compute_asset_profile",
        store=True,
        readonly=False,
    )
    
    @api.depends('product_id')
    def _compute_asset_profile(self):
        for record in self:
            if record.product_id and record.product_id.asset_profile_id:
                record.asset_profile_id = record.product_id.asset_profile_id
            else:
                record.product_id.asset_profile_id = False
    
class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    asset_count = fields.Integer(
        string="Assets",
        ondelete="restrict",
        check_company=True,
        compute="_compute_assets",
    )
    
    
    def action_view_assets(self):
        return {
            'name': _('It Assets'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.asset',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self._compute_assets())]
        }

    
    def _compute_assets(self):
        _logger.warning("_compute_assets"*100)
        assets_ids = []
        for stock_picking in self:
            for move in stock_picking.move_ids:
                for lot_id in move.lot_ids:
                    if lot_id.asset_id:
                       assets_ids.append(lot_id.asset_id.id)
            _logger.warning(f"{assets_ids=}")
            stock_picking.asset_count = len(assets_ids)
            _logger.warning(f"{stock_picking.asset_count=}")   
        return assets_ids
    
    def button_validate(self):
        res = super().button_validate()
        for stock_picking in self:
            for move in stock_picking.move_ids:
                if move.product_id.tracking == "serial":
                    for lot_id in move.lot_ids:
                        if move.asset_profile_id or lot_id.asset_profile_id and not lot_id.asset_id:
                            vals = lot_id._prepare_asset_vals(stock_picking, move)
                            lot_id.create_asset(vals)
                        elif lot_id.asset_id and lot_id.asset_id.state == "draft":
                            lot_id.update_partner_asset(stock_picking.partner_id)
                            #Change partner 
        
        
        return res

