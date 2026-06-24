from odoo import api, fields, models, _


class ProductCommodityQuality(models.Model):
    _name = 'product.commodity.quality'
    _description = 'Commodity Quality / Purity'
    _order = 'purity_percent desc'

    commodity_id = fields.Many2one('product.commodity', string='Commodity', required=True, ondelete='cascade',
                                    index=True)
    name = fields.Char(required=True)
    purity_percent = fields.Float(string='Purity %', digits=(16, 4), default=100.0)
    price_coefficient = fields.Float(string='Price Coefficient', digits=(16, 6), default=1.0,
                                      help='Multiplier against base commodity price. '
                                           'e.g. 24K=1.0, 22K=0.9167, 18K=0.75')

    gram_price = fields.Float(string='Price per Gram', digits=(16, 4), store=False,
                               compute='_compute_gram_price',
                               help='Computed price per gram based on latest commodity price')

    _sql_constraints = [
        ('name_commodity_uniq', 'unique(name, commodity_id)',
         'Quality name must be unique per commodity!'),
    ]

    @api.depends('commodity_id', 'commodity_id.price_ids', 'price_coefficient',
                 'commodity_id.grams_per_unit')
    def _compute_gram_price(self):
        for q in self:
            latest = self.env['product.commodity.price'].search([
                ('commodity_id', '=', q.commodity_id.id),
            ], order='date desc', limit=1)
            if latest and latest.price and q.commodity_id.grams_per_unit:
                q.gram_price = (latest.price / q.commodity_id.grams_per_unit) * q.price_coefficient
            else:
                q.gram_price = 0.0
