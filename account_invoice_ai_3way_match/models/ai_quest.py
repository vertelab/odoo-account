import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AIQuest(models.Model):
    _inherit = "ai.quest"

    def _process_file_content(self, session, partner_id, file_content, match_purchase_order=False):
        """Override: after AI creates the vendor bill, try to link to purchase orders."""
        move_id = super()._process_file_content(
            session, partner_id, file_content, match_purchase_order=match_purchase_order
        )
        if move_id and partner_id:
            self._try_match_purchase_order(move_id, partner_id)
        return move_id

    def _try_match_purchase_order(self, move_id, partner_id):
        """Find open POs for the vendor and link invoice lines to PO lines by product.
        Sets purchase_line_id on matched invoice lines so can_be_paid / release_to_pay
        work for the 3-way match."""
        move = self.env['account.move'].browse(move_id)

        # Guard: only vendor bills, and only if we have invoice lines
        if move.move_type not in ('in_invoice', 'in_refund'):
            return
        if not move.invoice_line_ids:
            return

        # Find open purchase orders for this partner
        open_pos = self.env['purchase.order'].search([
            ('partner_id', '=', partner_id.id),
            ('state', 'in', ('purchase', 'done')),
            ('invoice_status', '!=', 'invoiced'),
        ])
        if not open_pos:
            _logger.info(
                "account_invoice_ai_3way_match: no open POs for partner %s (move %s)",
                partner_id.name, move.name or move.id
            )
            return

        # Collect all PO lines from open POs, indexed by product
        po_lines_by_product = {}
        for po in open_pos:
            for po_line in po.order_line.filtered(lambda l: l.product_id):
                product_id = po_line.product_id.id
                if product_id not in po_lines_by_product:
                    po_lines_by_product[product_id] = []
                po_lines_by_product[product_id].append(po_line)

        matched = 0
        unmatched = 0
        for inv_line in move.invoice_line_ids.filtered(
            lambda l: l.display_type not in ('line_section', 'line_note')
        ):
            # Already linked? Skip
            if inv_line.purchase_line_id:
                continue

            product = inv_line.product_id
            if not product:
                # Try to find product by name via the robust lookup in account_invoice_ai
                name = inv_line.name or ''
                product = self._find_product(name)
                if product:
                    inv_line.product_id = product.id

            if product and product.id in po_lines_by_product:
                candidates = po_lines_by_product[product.id]
                # Pick the first candidate that still needs invoicing
                for po_line in candidates:
                    if po_line.qty_invoiced < po_line.product_qty:
                        inv_line.purchase_line_id = po_line.id
                        matched += 1
                        break
            else:
                unmatched += 1

        if matched or unmatched:
            _logger.info(
                "account_invoice_ai_3way_match: move %s — %d lines matched to POs, %d unmatched",
                move.name or move.id, matched, unmatched
            )
