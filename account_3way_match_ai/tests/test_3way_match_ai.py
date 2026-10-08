from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestThreeWayMatchAI(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user.groups_id |= cls.env.ref('purchase.group_purchase_user')
        cls.partner = cls.env['res.partner'].create({'name': 'Matchpartner'})
        cls.product = cls.env['product.product'].create({
            'name': 'Match Product',
            'standard_price': 100.0,
            'list_price': 150.0,
            'type': 'service',
            'purchase_method': 'receive',
        })

    def _create_order(self, qty=10, price=100.0):
        order = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'name': self.product.name,
                'product_id': self.product.id,
                'product_qty': qty,
                'product_uom': self.product.uom_id.id,
                'price_unit': price,
                'date_planned': fields.Datetime.now(),
            })],
        })
        order.button_confirm()
        return order

    def _create_bill(self, qty=5, price=100.0, ref=None):
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
            'ref': ref,
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': qty,
                'price_unit': price,
            })],
        })
        return move

    def test_match_unique_product(self):
        """En fakturarad med en produkt som finns på exakt en öppen PO-rad kopplas."""
        self._create_order()
        bill = self._create_bill()
        report = bill._match_purchase_order_lines()
        self.assertEqual(report['matched'], 1)
        self.assertEqual(report['unmatched'], 0)
        line = bill._billable_lines()
        self.assertTrue(line.purchase_line_id)

    def test_already_linked_line_untouched(self):
        """En redan kopplad rad lämnas orörd."""
        order = self._create_order()
        bill = self._create_bill()
        line = bill._billable_lines()
        line.purchase_line_id = order.order_line[0]
        report = bill._match_purchase_order_lines()
        self.assertEqual(report['matched'], 0)
        self.assertEqual(line.purchase_line_id, order.order_line[0])

    def test_no_open_order_line_reports_unmatched(self):
        """Utan öppen PO-rad lämnas raden okopplad och rapporteras."""
        bill = self._create_bill()
        report = bill._match_purchase_order_lines()
        self.assertEqual(report['matched'], 0)
        self.assertEqual(report['unmatched'], 1)
        self.assertEqual(report['anomalies'][0]['reason'], 'no_open_order_line')
        self.assertFalse(bill._billable_lines().purchase_line_id)

    def test_product_conflict_no_auto_link(self):
        """Flera öppna PO-rader med samma produkt ger produktkonflikt, ingen koppling."""
        self._create_order()
        self._create_order()
        bill = self._create_bill()
        report = bill._match_purchase_order_lines()
        self.assertEqual(report['matched'], 0)
        self.assertEqual(report['anomalies'][0]['reason'], 'product_conflict')
        self.assertFalse(bill._billable_lines().purchase_line_id)

    def test_match_drives_release_to_pay(self):
        """Kopplingen driver can_be_paid/release_to_pay — inte direkt skrivning."""
        order = self._create_order(qty=10)
        order.order_line[0].write({'qty_received': 5})
        bill = self._create_bill(qty=5)
        bill._match_purchase_order_lines()
        line = bill._billable_lines()
        self.assertEqual(line.can_be_paid, 'yes')
        self.assertEqual(bill.release_to_pay, 'yes')

    def test_price_deviation_detected(self):
        """Prisavvikelse mot inköpsordern rapporteras."""
        order = self._create_order(price=100.0)
        bill = self._create_bill(qty=5, price=42.0)
        bill._match_purchase_order_lines()
        anomalies = bill._find_anomalies()
        reasons = [a['reason'] for a in anomalies]
        self.assertIn('price_deviation', reasons)

    def test_quantity_deviation_detected(self):
        """Fakturerad kvantitet över mottagen/beställd rapporteras."""
        order = self._create_order(qty=10)
        order.order_line[0].write({'qty_received': 3})
        bill = self._create_bill(qty=5)
        bill._match_purchase_order_lines()
        anomalies = bill._find_anomalies()
        reasons = [a['reason'] for a in anomalies]
        self.assertIn('quantity_deviation', reasons)

    def test_duplicate_bill_detected(self):
        """En faktura med samma referens hos leverantören rapporteras som dubblett."""
        self._create_bill(ref='INV-001')
        bill2 = self._create_bill(ref='INV-001')
        anomalies = bill2._find_anomalies()
        reasons = [a['reason'] for a in anomalies]
        self.assertIn('duplicate', reasons)
