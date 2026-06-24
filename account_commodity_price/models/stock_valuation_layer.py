from odoo import api, fields, models, _


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    commodity_id = fields.Many2one('product.commodity', string='Commodity',
                                    related='product_id.commodity_id', store=True)
