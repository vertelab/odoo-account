# Copyright 2026 Vertel Sverige AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)
"""T/11823 - the deferred reference number follows the origin invoice."""

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestDeferredCode(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.partner = cls.env["res.partner"].create({"name": "T11823 Partner"})
        cls.expense_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "expense"),
                ("company_ids", "in", cls.company.id),
            ],
            limit=1,
        )
        cls.period_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "asset_current"),
                ("company_ids", "in", cls.company.id),
            ],
            limit=1,
        )
        cls.profile = cls.env["account.deferred.profile"].create(
            {
                "name": "T11823 Profile",
                "rec_type": "deferred_expense",
                "account_depreciation_id": cls.period_account.id,
                "account_expense_id": cls.expense_account.id,
                "journal_id": cls.journal.id,
                "method_number": 3,
                "method_period": "month",
                "company_id": cls.company.id,
            }
        )

    def _make_bill(self):
        return self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "journal_id": self.journal.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "T11823 line",
                            "quantity": 1.0,
                            "price_unit": 300.0,
                            "account_id": self.expense_account.id,
                        },
                    )
                ],
            }
        )

    def _periodise(self, bill):
        line = bill.invoice_line_ids.filtered(
            lambda l: l.display_type == "product"
        )[:1]
        return self.env["account.deferred"].create(
            {
                "name": "T11823 deferred",
                "profile_id": self.profile.id,
                "rec_type": "deferred_expense",
                "partner_id": self.partner.id,
                "company_id": self.company.id,
                "account_depreciation_id": self.period_account.id,
                "account_expense_id": self.expense_account.id,
                "journal_id": self.journal.id,
                "amount_total": 300.0,
                "date_start": fields.Date.today(),
                "method_period": "month",
                "method_number": 3,
                "move_line_id": line.id,
            }
        )

    # ── 1. Draft invoice -> placeholder ─────────────────────────────────
    def test_01_draft_invoice_gives_placeholder(self):
        bill = self._make_bill()
        self.assertEqual(bill.state, "draft")
        deferred = self._periodise(bill)
        self.assertIn(deferred.code, (False, "/"))

    # ── 2. Posting the invoice fills the reference ──────────────────────
    def test_02_posting_fills_reference(self):
        bill = self._make_bill()
        deferred = self._periodise(bill)
        bill.action_post()
        self.assertNotEqual(bill.name, "/")
        deferred.invalidate_recordset(["code"])
        self.assertEqual(deferred.code, bill.name)

    # ── 3. Posted invoice -> reference immediately ──────────────────────
    def test_03_posted_invoice_gives_reference(self):
        bill = self._make_bill()
        bill.action_post()
        deferred = self._periodise(bill)
        self.assertEqual(deferred.code, bill.name)

    # ── 4. Manual reference survives while the invoice has no number ────
    def test_04_manual_reference_kept(self):
        bill = self._make_bill()
        deferred = self._periodise(bill)
        deferred.code = "MY-REF-42"
        deferred.invalidate_recordset(["code"])
        self.assertEqual(deferred.code, "MY-REF-42")

    # ── 5. Closed entries are never touched ─────────────────────────────
    def test_05_closed_entry_untouched(self):
        bill = self._make_bill()
        deferred = self._periodise(bill)
        deferred.code = "FROZEN"
        deferred.state = "close"
        bill.action_post()
        deferred.invalidate_recordset(["code"])
        self.assertEqual(deferred.code, "FROZEN")

    # ── 6. Smart button opens the origin invoice ────────────────────────
    def test_06_open_origin_move(self):
        bill = self._make_bill()
        deferred = self._periodise(bill)
        action = deferred.action_open_origin_move()
        self.assertEqual(action["res_model"], "account.move")
        self.assertEqual(action["res_id"], bill.id)

    # ── 7. Backfill is idempotent and only touches empty values ─────────
    def test_07_backfill(self):
        from odoo.addons.account_deferred_revenue_expenses.hooks import (
            _backfill_deferred_code,
        )

        bill = self._make_bill()
        bill.action_post()
        deferred = self._periodise(bill)
        # Simulate the legacy state: empty reference on a posted invoice.
        deferred.flush_recordset()
        self.env.cr.execute(
            "UPDATE account_deferred SET code = NULL WHERE id = %s",
            (deferred.id,),
        )
        deferred.invalidate_recordset(["code"])
        _backfill_deferred_code(self.env)
        deferred.invalidate_recordset(["code"])
        self.assertEqual(deferred.code, bill.name)
        # Second run changes nothing.
        _backfill_deferred_code(self.env)
        deferred.invalidate_recordset(["code"])
        self.assertEqual(deferred.code, bill.name)
