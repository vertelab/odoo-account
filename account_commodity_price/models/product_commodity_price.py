from odoo import api, fields, models, _


class ProductCommodityPrice(models.Model):
    _name = 'product.commodity.price'
    _description = 'Commodity Price Record'
    _order = 'date desc, id desc'
    _rec_name = 'display_name'

    commodity_id = fields.Many2one('product.commodity', string='Commodity', required=True, ondelete='cascade',
                                    index=True)
    date = fields.Date(required=True, default=fields.Date.today, index=True)
    price = fields.Monetary(string='Price', currency_field='currency_id', required=True)
    currency_id = fields.Many2one('res.currency', required=True,
                                   default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company,
                                  required=True)
    notes = fields.Text(string='Notes')
    display_name = fields.Char(compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('unique_price_per_day', 'unique(commodity_id, date, company_id)',
         'Only one price per day allowed per commodity!'),
        ('price_positive', 'CHECK(price >= 0)', 'Price must be non-negative.'),
    ]

    @api.depends('commodity_id', 'date', 'price', 'currency_id')
    def _compute_display_name(self):
        for r in self:
            commodity_name = r.commodity_id.code if r.commodity_id else ''
            r.display_name = f'[{commodity_name}] {r.date}: {r.price} {r.currency_id.name}'
