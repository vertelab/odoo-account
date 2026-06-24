from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_commodity_raw_material = fields.Boolean(string='Commodity Raw Material',
                                                help='Products that track commodity price')
    commodity_id = fields.Many2one('product.commodity', string='Commodity',
                                    domain=[('active', '=', True)])
    commodity_quality_id = fields.Many2one('product.commodity.quality',
                                            string='Commodity Quality',
                                            domain="[('commodity_id', '=', commodity_id)]")
    commodity_weight = fields.Float(string='Commodity Weight (g)',
                                     help='Weight of commodity in grams',
                                     digits=(16, 4))
    commodity_price_auto = fields.Boolean(string='Auto Price from Commodity',
                                           help='Automatically compute product price from commodity price')
    commodity_price_type = fields.Selection([
        ('component', 'BOM Component (raw material)'),
        ('finished', 'Finished Good (price = quality_price * weight)'),
    ], default='component')

    commodity_suggested_price = fields.Float(string='Suggested Price',
                                              compute='_compute_commodity_suggested_price',
                                              digits='Product Price')

    @api.depends('commodity_quality_id', 'commodity_weight', 'commodity_price_auto')
    def _compute_commodity_suggested_price(self):
        for p in self:
            if p.commodity_price_auto and p.commodity_quality_id and p.commodity_weight:
                p.commodity_suggested_price = p.commodity_quality_id.gram_price * p.commodity_weight
            else:
                p.commodity_suggested_price = 0.0

    def action_apply_commodity_price(self):
        for p in self:
            if p.commodity_suggested_price:
                p.list_price = p.commodity_suggested_price

    @api.onchange('commodity_price_auto')
    def _onchange_commodity_price_auto(self):
        if self.commodity_price_auto:
            self.list_price = self.commodity_suggested_price


class ProductProduct(models.Model):
    _inherit = 'product.product'

    commodity_id = fields.Many2one(related='product_tmpl_id.commodity_id', store=True)
    commodity_quality_id = fields.Many2one(related='product_tmpl_id.commodity_quality_id', store=True)
    commodity_weight = fields.Float(related='product_tmpl_id.commodity_weight')
    commodity_price_auto = fields.Boolean(related='product_tmpl_id.commodity_price_auto')
    commodity_price_type = fields.Selection(related='product_tmpl_id.commodity_price_type')
    is_commodity_raw_material = fields.Boolean(related='product_tmpl_id.is_commodity_raw_material')
