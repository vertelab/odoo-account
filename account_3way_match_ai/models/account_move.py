"""AI-assisterad 3-vägsmatchning.

Medarbetaren (ai.coworker) gör matchningen. Den här modellen tillhandahåller
den deterministiska kärnan som medarbetaren och dess agenter använder:

* `_match_purchase_order_lines()` — kopplar fakturarader till öppna
  inköpsorderrader via `purchase_line_id` och rapporterar anomalier.
* `_find_anomalies()` — jämför kopplade rader mot inköpsordern.

Modulen sätter ALDRIG `release_to_pay` eller `release_to_pay_manual` direkt.
När `purchase_line_id` sätts beräknar `account_3way_match_ce` tillståndet.
"""

import logging

from odoo import models
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _billable_lines(self):
        """Fakturans rader som bär kvantitet och pris."""
        self.ensure_one()
        return self.invoice_line_ids.filtered(
            lambda line: line.display_type not in ('line_section', 'line_subsection', 'line_note'))

    def _open_purchase_lines_by_product(self):
        """Öppna inköpsorderrader för fakturans leverantör, per produkt."""
        self.ensure_one()
        orders = self.env['purchase.order'].search([
            ('partner_id', '=', self.partner_id.id),
            ('state', 'in', ('purchase', 'done')),
            ('invoice_status', '!=', 'invoiced'),
        ])
        by_product = {}
        for order in orders:
            for order_line in order.order_line.filtered(lambda l: l.product_id):
                by_product.setdefault(order_line.product_id.id, []).append(order_line)
        return by_product

    def _match_purchase_order_lines(self):
        """Koppla fakturarader till öppna inköpsorderrader.

        Returnerar en rapport: {'matched': int, 'unmatched': int,
        'anomalies': [{'line_id', 'reason'}]}. Redan kopplade rader lämnas
        orörda. Vid osäkerhet (ingen träff eller flera kandidater) lämnas
        raden okopplad och rapporteras — ingen gissning.
        """
        self.ensure_one()
        report = {'matched': 0, 'unmatched': 0, 'anomalies': []}
        if self.move_type not in ('in_invoice', 'in_refund'):
            return report

        by_product = self._open_purchase_lines_by_product()
        for line in self._billable_lines():
            if line.purchase_line_id:
                continue
            product = line.product_id
            if not product:
                report['unmatched'] += 1
                report['anomalies'].append({'line_id': line.id, 'reason': 'no_product'})
                continue
            candidates = by_product.get(product.id, [])
            if len(candidates) == 1:
                line.purchase_line_id = candidates[0]
                report['matched'] += 1
            elif len(candidates) > 1:
                report['unmatched'] += 1
                report['anomalies'].append({'line_id': line.id, 'reason': 'product_conflict'})
            else:
                report['unmatched'] += 1
                report['anomalies'].append({'line_id': line.id, 'reason': 'no_open_order_line'})
        return report

    def _find_anomalies(self):
        """Jämför kopplade fakturarader mot inköpsordern.

        Returnerar en lista av {'line_id', 'reason'}: 'price_deviation',
        'quantity_deviation' eller 'duplicate'.
        """
        self.ensure_one()
        anomalies = []
        for line in self._billable_lines():
            order_line = line.purchase_line_id
            if not order_line:
                continue
            if line._price_differs_from_order(order_line):
                anomalies.append({'line_id': line.id, 'reason': 'price_deviation'})
            if line._quantity_exceeds_order(order_line):
                anomalies.append({'line_id': line.id, 'reason': 'quantity_deviation'})
        if self._has_duplicate_bill():
            anomalies.append({'line_id': False, 'reason': 'duplicate'})
        return anomalies

    def _has_duplicate_bill(self):
        """True om en annan faktura med samma referens finns hos leverantören."""
        self.ensure_one()
        if not self.ref:
            return False
        return bool(self.env['account.move'].search_count([
            ('id', '!=', self.id),
            ('move_type', '=', self.move_type),
            ('partner_id', '=', self.partner_id.id),
            ('ref', '=', self.ref),
        ]))


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _quantity_exceeds_order(self, order_line):
        """True om fakturerad kvantitet överstiger mottagen eller beställd."""
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get('Product Unit')
        if float_compare(self.quantity, order_line.qty_received, precision_digits=precision) > 0:
            return True
        return float_compare(self.quantity, order_line.product_qty, precision_digits=precision) > 0
