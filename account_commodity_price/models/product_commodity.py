from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, timedelta
import requests
import logging

_logger = logging.getLogger(__name__)


class ProductCommodity(models.Model):
    _name = 'product.commodity'
    _description = 'Commodity'
    _order = 'code, name'
    _rec_name = 'display_name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)
    active = fields.Boolean(default=True)
    category = fields.Selection([
        ('precious_metal', 'Precious Metal'),
        ('base_metal', 'Base Metal'),
        ('energy', 'Energy'),
        ('other', 'Other'),
    ], default='precious_metal', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True,
                              domain=[('category_id', '=', 'uom.product_uom_categ_kgm')],
                              default=lambda self: self.env.ref('uom.product_uom_oz', raise_if_not_found=False))
    grams_per_unit = fields.Float(string='Grams per Unit',
                                   help='Conversion factor: grams per one unit of measure',
                                   default=31.1035)
    currency_id = fields.Many2one('res.currency', string='Base Currency', required=True,
                                   default=lambda self: self.env.company.currency_id)

    journal_id = fields.Many2one('account.journal', string='Revaluation Journal',
                                  domain=[('is_commodity_journal', '=', True),
                                          ('type', '=', 'general')])
    gain_account_id = fields.Many2one('account.account', string='Gain Account',
                                       domain=[('account_type', '=', 'income')])
    loss_account_id = fields.Many2one('account.account', string='Loss Account',
                                       domain=[('account_type', '=', 'expense')])
    valuation_account_id = fields.Many2one('account.account', string='Stock Valuation Account')
    price_diff_account_id = fields.Many2one('account.account', string='Price Difference Account')

    api_provider = fields.Selection([
        ('aurumrates', 'AurumRates (free, no key)'),
        ('goldapi_io', 'GoldAPI.io (key required)'),
    ], default='aurumrates', required=True)
    api_symbol = fields.Char(string='API Symbol',
                              help='e.g. GC=F for AurumRates, XAU for GoldAPI.io',
                              default='GC=F')
    api_key = fields.Char(string='API Key')
    api_last_fetch = fields.Datetime(string='Last API Fetch')
    api_last_error = fields.Text(string='Last API Error')

    quality_ids = fields.One2many('product.commodity.quality', 'commodity_id', string='Qualities',
                                   copy=True)
    price_ids = fields.One2many('product.commodity.price', 'commodity_id', string='Prices')

    latest_price = fields.Monetary(string='Latest Price', compute='_compute_latest_price', store=True,
                                    currency_field='currency_id')
    latest_price_date = fields.Date(string='Latest Price Date', compute='_compute_latest_price', store=True)
    latest_currency_id = fields.Many2one('res.currency', compute='_compute_latest_price')

    price_change_pct = fields.Float(string='Price Change %', compute='_compute_price_change')
    inventory_qty = fields.Float(string='Inventory Qty', compute='_compute_inventory')
    inventory_value = fields.Float(string='Inventory Value', compute='_compute_inventory')
    product_count = fields.Integer(string='Product Count', compute='_compute_product_count')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Commodity code must be unique!'),
    ]

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for c in self:
            c.display_name = f'[{c.code}] {c.name}'

    @api.depends('price_ids', 'price_ids.price', 'price_ids.date')
    def _compute_latest_price(self):
        for c in self:
            latest = self.env['product.commodity.price'].search([
                ('commodity_id', '=', c.id),
            ], order='date desc', limit=1)
            c.latest_price = latest.price if latest else 0.0
            c.latest_price_date = latest.date if latest else False
            c.latest_currency_id = latest.currency_id if latest else c.currency_id

    @api.depends('price_ids', 'price_ids.price')
    def _compute_price_change(self):
        for c in self:
            latest = self.env['product.commodity.price'].search([
                ('commodity_id', '=', c.id),
            ], order='date desc', limit=1)
            previous = self.env['product.commodity.price'].search([
                ('commodity_id', '=', c.id),
            ], order='date desc', limit=1, offset=1)
            if latest and previous and previous.price:
                c.price_change_pct = ((latest.price - previous.price) / previous.price) * 100.0
            else:
                c.price_change_pct = 0.0

    def _compute_inventory(self):
        for c in self:
            products = self.env['product.product'].search([
                ('commodity_id', '=', c.id),
            ])
            total_qty = 0.0
            total_value = 0.0
            for p in products:
                qty = p.qty_available
                total_qty += qty
                total_value += qty * p.standard_price
            c.inventory_qty = total_qty
            c.inventory_value = total_value

    def _compute_product_count(self):
        count_data = self.env['product.product'].read_group(
            [('commodity_id', 'in', self.ids)],
            ['commodity_id'],
            ['commodity_id'],
        )
        counts = {d['commodity_id'][0]: d['commodity_id_count'] for d in count_data}
        for c in self:
            c.product_count = counts.get(c.id, 0)

    def action_fetch_price(self):
        self._fetch_prices()

    def _fetch_prices(self):
        for commodity in self:
            try:
                if commodity.api_provider == 'aurumrates':
                    self._fetch_aurumrates(commodity)
                elif commodity.api_provider == 'goldapi_io':
                    self._fetch_goldapi(commodity)
                commodity.write({
                    'api_last_fetch': fields.Datetime.now(),
                    'api_last_error': False,
                })
            except Exception as e:
                _logger.error('Failed to fetch price for %s: %s', commodity.code, str(e))
                commodity.write({
                    'api_last_fetch': fields.Datetime.now(),
                    'api_last_error': str(e),
                })

    def _fetch_aurumrates(self, commodity):
        symbol = commodity.api_symbol or 'GC=F'
        url = f'https://aurumrates.com/api/chart?symbol={symbol}&range=1d&interval=1d'
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        price = data.get('regularMarketPrice')
        if not price:
            raise UserError(_('No price found in AurumRates response'))
        self._create_price_record(commodity, price)

    def _fetch_goldapi(self, commodity):
        symbol = commodity.api_symbol or 'XAU'
        currency = commodity.currency_id.name or 'USD'
        api_key = commodity.api_key
        if not api_key:
            raise UserError(_('API Key required for GoldAPI.io'))
        url = f'https://www.goldapi.io/api/{symbol}/{currency}'
        headers = {'x-access-token': api_key}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        price = data.get('price')
        if not price:
            raise UserError(_('No price found in GoldAPI.io response'))
        price_rec = self._create_price_record(commodity, price)
        if commodity.quality_ids and data.get('price_gram_24k'):
            for quality in commodity.quality_ids:
                gram_key = f'price_gram_{quality.name.lower().replace(" ", "_")}'
                gram_price = data.get(gram_key)
                if gram_price:
                    quality.price_per_gram = gram_price

    def _create_price_record(self, commodity, price):
        today = date.today()
        existing = self.env['product.commodity.price'].search([
            ('commodity_id', '=', commodity.id),
            ('date', '=', today),
        ], limit=1)
        if existing:
            existing.price = price
            return existing
        return self.env['product.commodity.price'].create({
            'commodity_id': commodity.id,
            'date': today,
            'price': price,
            'currency_id': commodity.currency_id.id,
            'company_id': self.env.company.id,
        })

    def action_revaluate(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'commodity.revaluation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_commodity_id': self.id,
                'default_company_id': self.env.company.id,
            },
        }

    @api.model
    def _cron_fetch_prices(self):
        commodities = self.search([('active', '=', True)])
        commodities._fetch_prices()
        return True
