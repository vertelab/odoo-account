# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    """Let a payment follow its bill's state without ever being booked.

    A payment order whose method has `pending_until_reconciliation = True`
    books nothing at upload time (see AccountPaymentOrder.generated2uploaded).
    When the bank transaction is imported, the reconciliation models match it
    directly against the bill, so the bill reaches 'paid' on its own — the
    payment plays no part in the accounting.

    The payment is therefore a marker only. It must show 'in_process'
    (pågående behandling) while the bill is pending and 'paid' once the bill is
    settled, but it must never create a journal entry: the bank transaction
    already covers the bill, so booking the payment too would duplicate the
    movement on the payable account and leave that account out of balance.

    Note the state values: account.payment has no 'in_payment' — that value
    belongs to account.move.payment_state. The payment's own pending value is
    'in_process', which the UI renders as "Pågående behandling".

    Odoo's account.payment.write() books a payment as soon as 'state' is set to
    'in_process' or 'paid' on a payment without a move_id. The journal entry is
    built in _generate_journal_entry(), and _check_move_id() forbids leaving
    'draft' without one. Both are bypassed here for payments belonging to a
    pending order, so their state follows the bill while nothing is booked.

    Odoo's _compute_state() only promotes a payment that is 'in_process' and
    reconciled, and its stat buttons read the reconciled bills and statement
    lines. A pending payment has neither, so they are derived here from the
    payment lines and the bill's reconciliation instead.
    """

    _inherit = "account.payment"

    pending_settlement_move_ids = fields.Many2many(
        comodel_name="account.move",
        relation="account_payment_pending_settlement_move_rel",
        column1="payment_id",
        column2="move_id",
        string="Settlement Entries",
        compute="_compute_stat_buttons_from_reconciliation",
        help="The bank transaction entries that settled this payment's bills. "
        "A pending payment is never booked or reconciled itself, so the "
        "entries are reached through the bills it is queued for.",
    )

    pending_settlement_move_count = fields.Integer(
        string="# Settlement Entries",
        compute="_compute_stat_buttons_from_reconciliation",
    )

    def _is_pending_order_payment(self):
        """True when this payment belongs to a pending-until-reconciliation
        order and therefore must not be booked."""
        self.ensure_one()
        return bool(
            self.payment_order_id
            and self.payment_order_id.payment_method_id.pending_until_reconciliation
        )

    def _get_pending_bills(self):
        """The bills this payment is queued for, taken from the payment lines.

        A pending payment has no reconciliation, so the bills cannot be read
        from reconciled_bill_ids — the payment lines are the only link.
        """
        self.ensure_one()
        return self.payment_line_ids.move_line_id.move_id

    def _get_pending_settlement_moves(self):
        """The bank transaction entries that settled this payment's bills.

        The payment itself is never reconciled, so the entries are reached
        through the bill: its payable line is reconciled against the bank
        transaction's counterpart, whose move carries statement_line_id.
        """
        self.ensure_one()
        bills = self._get_pending_bills()
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
        return counterpart_lines.move_id.filtered(lambda move: move.statement_line_id)

    def _generate_journal_entry(
        self, write_off_line_vals=None, force_balance=None, line_ids=None
    ):
        """Skip the journal entry for payments of a pending order.

        These payments are markers: the bank transaction settles the bill, so
        there is nothing for the payment to book. Their state is still written
        by the caller, which is what makes them follow the bill.
        """
        to_book = self.filtered(lambda p: not p._is_pending_order_payment())
        if not to_book:
            return
        return super(
            AccountPayment, to_book
        )._generate_journal_entry(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance,
            line_ids=line_ids,
        )

    @api.constrains("state", "move_id")
    def _check_move_id(self):
        """Allow a pending-order payment to be confirmed without an entry.

        Odoo requires a journal entry for any payment that leaves 'draft'.
        A pending-order payment is a marker: the bank transaction settles the
        bill, so the payment is never booked and legitimately has no entry.
        """
        super(
            AccountPayment,
            self.filtered(lambda p: not p._is_pending_order_payment()),
        )._check_move_id()

    @api.depends(
        "payment_order_id",
        "payment_order_id.state",
        "payment_order_id.payment_method_id.pending_until_reconciliation",
        "payment_line_ids.move_line_id.move_id.payment_state",
    )
    def _compute_state(self):
        """Derive the state of a pending-order payment from its bill.

        Odoo only promotes a payment that is 'in_process' and reconciled. A
        pending-order payment is neither: it is never booked and never
        reconciled, so its state is read from the bill it points at.
        """
        super()._compute_state()

        for payment in self.filtered(
            lambda p: p._is_pending_order_payment() and not p.move_id
        ):
            bills = payment._get_pending_bills()
            if not bills:
                continue
            if all(bill.payment_state == "paid" for bill in bills):
                payment._set_pending_state("paid")
            elif all(
                bill.payment_state in ("paid", "in_payment") for bill in bills
            ):
                payment._set_pending_state("in_process")

    def _set_pending_state(self, state):
        """Write the state without triggering the journal entry creation.

        The field is computed, so a plain assignment would recurse through
        _compute_state(). The value is written straight to the database and the
        cache is invalidated, bypassing both the compute and the write()
        override that would book the payment.

        Only values from the field's own selection may be used:
        account.payment has no 'in_payment' — that belongs to
        account.move.payment_state.
        """
        self.ensure_one()
        if self.state == state:
            return
        allowed = dict(self._fields["state"].get_description(self.env)["selection"])
        if state not in allowed:
            raise ValueError(
                "Invalid account.payment.state %r; expected one of %s"
                % (state, sorted(allowed))
            )
        self.env.cr.execute(
            "UPDATE account_payment SET state = %s WHERE id = %s",
            (state, self.id),
        )
        self.invalidate_recordset(["state"])

    @api.depends(
        "payment_order_id",
        "payment_order_id.payment_method_id.pending_until_reconciliation",
        "payment_line_ids.move_line_id.move_id",
    )
    def _compute_stat_buttons_from_reconciliation(self):
        """Show the bill and the settlement entry of a pending payment.

        Odoo derives the stat buttons from the reconciliations, which a pending
        payment never has. Both are taken from the payment lines instead, so
        the standard 'Bill' button and the 'Journal Entry' button open them.
        """
        super()._compute_stat_buttons_from_reconciliation()

        for payment in self:
            payment.pending_settlement_move_ids = False
            payment.pending_settlement_move_count = 0

        for payment in self.filtered(
            lambda p: p._is_pending_order_payment() and not p.move_id
        ):
            bills = payment._get_pending_bills()
            if bills:
                payment.reconciled_bill_ids |= bills
                payment.reconciled_bills_count = len(payment.reconciled_bill_ids)

            moves = payment._get_pending_settlement_moves()
            if moves:
                payment.pending_settlement_move_ids = moves
                payment.pending_settlement_move_count = len(moves)

    def button_open_pending_settlement_moves(self):
        """Open the settlement entries of this payment.

        One entry opens its form; several open a list — the same pattern as
        account.payment.button_open_bills. The base action carries a views list
        that would otherwise force the list view, so it is reset.
        """
        self.ensure_one()
        moves = self.pending_settlement_move_ids
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_journal_line"
        )
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
