from odoo.tests import common, tagged


@tagged('-at_install', 'post_install')
class TestCommodity(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        commodity_model = cls.env['product.commodity']
        quality_model = cls.env['product.commodity.quality']
        price_model = cls.env['product.commodity.price']

        cls.commodity = commodity_model.create({
            'name': 'Test Gold',
            'code': 'TXAU',
            'category': 'precious_metal',
            'uom_id': cls.env.ref('uom.product_uom_oz').id,
            'grams_per_unit': 31.1035,
            'currency_id': cls.env.ref('base.USD').id,
            'api_provider': 'aurumrates',
            'api_symbol': 'GC=F',
        })

        cls.quality_24k = quality_model.create({
            'commodity_id': cls.commodity.id,
            'name': '24K',
            'purity_percent': 99.99,
            'price_coefficient': 1.0,
        })
        cls.quality_18k = quality_model.create({
            'commodity_id': cls.commodity.id,
            'name': '18K',
            'purity_percent': 75.0,
            'price_coefficient': 0.75,
        })

        cls.price_1 = price_model.create({
            'commodity_id': cls.commodity.id,
            'date': '2026-06-01',
            'price': 4000.0,
            'currency_id': cls.env.ref('base.USD').id,
            'company_id': cls.env.company.id,
        })
        cls.price_2 = price_model.create({
            'commodity_id': cls.commodity.id,
            'date': '2026-06-02',
            'price': 4100.0,
            'currency_id': cls.env.ref('base.USD').id,
            'company_id': cls.env.company.id,
        })

    def test_commodity_creation(self):
        self.assertEqual(self.commodity.code, 'TXAU')
        self.assertEqual(self.commodity.name, 'Test Gold')
        self.assertEqual(len(self.commodity.quality_ids), 2)

    def test_price_change_percentage(self):
        self.commodity._compute_price_change()
        self.assertAlmostEqual(self.commodity.price_change_pct, 2.5, places=1)

    def test_price_display_name(self):
        expected = '[TXAU] 2026-06-01: 4000.0 USD'
        self.assertEqual(self.price_1.display_name, expected)

    def test_quality_gram_price(self):
        self.quality_24k._compute_gram_price()
        expected = 4100.0 / 31.1035 * 1.0
        self.assertAlmostEqual(self.quality_24k.gram_price, expected, places=2)

        self.quality_18k._compute_gram_price()
        expected_18k = 4100.0 / 31.1035 * 0.75
        self.assertAlmostEqual(self.quality_18k.gram_price, expected_18k, places=2)

    def test_unique_price_constraint(self):
        with self.cr.savepoint():
            with self.assertRaises(Exception):
                self.env['product.commodity.price'].create({
                    'commodity_id': self.commodity.id,
                    'date': '2026-06-02',
                    'price': 4200.0,
                    'currency_id': self.env.ref('base.USD').id,
                    'company_id': self.env.company.id,
                })

    def test_product_template_commodity_fields(self):
        product = self.env['product.template'].create({
            'name': 'Gold Ring',
            'is_commodity_raw_material': True,
            'commodity_id': self.commodity.id,
            'commodity_quality_id': self.quality_24k.id,
            'commodity_weight': 10.0,
        })
        self.assertTrue(product.is_commodity_raw_material)
        self.assertEqual(product.commodity_id, self.commodity)
        self.assertEqual(product.commodity_quality_id, self.quality_24k)
        self.assertEqual(product.commodity_weight, 10.0)

    def test_cron_method(self):
        result = self.env['product.commodity']._cron_fetch_prices()
        self.assertTrue(result)
