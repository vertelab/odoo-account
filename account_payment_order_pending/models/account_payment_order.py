# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def generated2uploaded(self):
        """Override to skip posting and reconciliation for pending methods.

        When the payment method has `pending_until_reconciliation = True`, the
        order transitions to "uploaded" WITHOUT creating any journal entry for
        its payments: nothing may be booked before the bank confirms the
        movement. The payments stay unbooked and the bills read 'in_payment'
        (pågående) because they are linked to a payment order — see
        AccountMove._is_pending_bank_settlement().

        The payments are flagged 'in_process' at the same moment, so the
        payment follows the bill from the start. Their state is derived again
        when the bank settles the bill (AccountPayment._compute_state).

        For manual/standard payment methods (pending_until_reconciliation =
        False), the original behavior is preserved: payments are posted and
        reconciled.
        """
        self.ensure_one()

        if self.payment_method_id.pending_until_reconciliation:
            # Pending mode: no journal entry, no reconciliation.
            _logger.info(
                "Payment order %s (method: %s): pending_until_reconciliation=True, "
                "skipping payment posting and reconciliation. "
                "Invoices remain in_payment.",
                self.name,
                self.payment_method_id.code,
            )
            self.write(
                {
                    "state": "uploaded",
                    "date_uploaded": fields.Date.context_today(self),
                }
            )
            # Recompute payment_state on the invoices so they are flagged
            # 'in_payment' even though no journal entry exists, then let the
            # payments follow them.
            moves = self.payment_line_ids.move_line_id.move_id
            if moves:
                moves._compute_payment_state()
            self.payment_ids._compute_state()
            return True
        else:
            # Standard mode: keep existing behavior
            return super().generated2uploaded()

    @api.depends(
        "payment_method_id.pending_until_reconciliation",
        "payment_line_ids.move_line_id.move_id",
        "payment_line_ids.move_line_id.move_id.payment_state",
    )
    def _compute_move_count(self):
        """Count the journal entries behind a pending order as well.

        A pending order books nothing, so OCA's count — which reads the moves
        carrying payment_order_id — is zero. The entries that matter are the
        bank transactions that settled the bills, reached through each bill's
        reconciliation. Counting them makes the standard 'Journal Entries'
        button open them.
        """
        super()._compute_move_count()

        for order in self.filtered(
            lambda o: o.payment_method_id.pending_until_reconciliation
        ):
            moves = order._get_pending_settlement_moves()
            if moves:
                order.move_count = len(moves)

    def _get_pending_settlement_moves(self):
        """The bank transaction entries that settled this order's bills."""
        self.ensure_one()
        bills = self.payment_line_ids.move_line_id.move_id
        if not bills:
            return self.env["account.move"]

        payable_lines = bills.line_ids.filtered(
            lambda line: line.account_id.account_type
            in ("asset_receivable", "liability_payable")
        )
        counterpart_lines = (
            payable_lines.matched_debit_ids.debit_move_id
            | payable_lines.matched_credit_ids.credit_move_id
        )
        return counterpart_lines.move_id.filtered(
            lambda move: move.statement_line_id
        )

    def action_move_journal_line(self):
        """Open the settlement entries for a pending order.

        OCA's action filters on payment_order_id, which no settlement entry
        carries. For a pending order the entries are listed explicitly.
        """
        self.ensure_one()
        if not self.payment_method_id.pending_until_reconciliation:
            return super().action_move_journal_line()

        moves = self._get_pending_settlement_moves()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_journal_line"
        )
        ctx = self.env.context.copy()
        ctx.update({"search_default_misc_filter": 0})
        action["context"] = ctx
        # One entry: open it. Several: list them. The base action carries a
        # views list that would otherwise force the list view, so it is reset
        # in both branches — same pattern as account.payment.button_open_bills.
        action.update({"views": False, "view_id": False})
        if len(moves) == 1:
            action.update({"view_mode": "form", "res_id": moves.id})
        else:
            action.update(
                {
                    "view_mode": "list,form",
                    "domain": [("id", "in", moves.ids)],
                }
            )
        return action
