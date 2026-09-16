# Copyright 2026 Vertel AB
# SPDX-License-Identifier: AGPL-3
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestBillApproval(TransactionCase):
    """Tests for the vendor bill approval workflow."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.approver = cls.env["res.users"].create({
            "name": "Test Approver",
            "login": "test_approver_bill",
            "email": "test_approver_bill@example.com",
            "company_id": cls.company.id,
            "company_ids": [(6, 0, [cls.company.id])],
            "groups_id": [(6, 0, [
                cls.env.ref("base.group_user").id,
                cls.env.ref("account.group_account_invoice").id,
                cls.env.ref(
                    "account_bill_approval.group_bill_approval_user"
                ).id,
            ])],
        })
        cls.other_approver = cls.env["res.users"].create({
            "name": "Other Approver",
            "login": "test_approver_bill_2",
            "email": "test_approver_bill_2@example.com",
            "company_id": cls.company.id,
            "company_ids": [(6, 0, [cls.company.id])],
            "groups_id": [(6, 0, [
                cls.env.ref("base.group_user").id,
                cls.env.ref("account.group_account_invoice").id,
                cls.env.ref(
                    "account_bill_approval.group_bill_approval_user"
                ).id,
            ])],
        })
        cls.vendor = cls.env["res.partner"].create({
            "name": "Test Vendor AB",
            "bill_approving_user_ids": [(6, 0, [cls.approver.id])],
        })
        cls.bill = cls.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": cls.vendor.id,
            "invoice_date": "2026-01-01",
            "invoice_line_ids": [(0, 0, {
                "name": "Test line",
                "quantity": 1.0,
                "price_unit": 100.0,
                "account_id": cls.env["account.account"].search(
                    [("account_type", "=", "expense")], limit=1
                ).id,
            })],
        })

    # ------------------------------------------------------------------
    # T/11311 — approvers must be freely selectable
    # ------------------------------------------------------------------
    def test_approver_is_freely_selectable(self):
        """A user not configured on the vendor can still be added."""
        self.bill.approving_user_ids = [(0, 0, {
            "user_id": self.other_approver.id,
        })]
        self.assertIn(
            self.other_approver,
            self.bill.approving_user_ids.mapped("user_id"),
            "Any user must be selectable as approver (T/11311).",
        )

    def test_vendor_approvers_are_only_a_suggestion(self):
        """Vendor approvers are pre-filled but removable."""
        self.bill.onchange_partner_set_approvers()
        self.assertIn(
            self.approver,
            self.bill.approving_user_ids.mapped("user_id"),
        )
        # Remove the suggested approver — must be allowed.
        self.bill.approving_user_ids = [(5, 0, 0)]
        self.assertFalse(self.bill.approving_user_ids)

    def test_duplicate_approver_rejected(self):
        self.bill.approving_user_ids = [(0, 0, {"user_id": self.approver.id})]
        with self.assertRaises(ValidationError):
            self.bill.approving_user_ids = [(0, 0, {
                "user_id": self.approver.id,
            })]

    # ------------------------------------------------------------------
    # Posting guard
    # ------------------------------------------------------------------
    def test_post_blocked_while_pending(self):
        self.bill.approving_user_ids = [(0, 0, {"user_id": self.approver.id})]
        with self.assertRaises(ValidationError):
            self.bill.action_post()

    def test_post_allowed_when_approved(self):
        line = self.env["bill.approval.user.line"].create({
            "move_id": self.bill.id,
            "user_id": self.approver.id,
            "state": "done",
        })
        self.assertTrue(line)
        self.bill.action_post()
        self.assertEqual(self.bill.state, "posted")

    # ------------------------------------------------------------------
    # Approve / reject
    # ------------------------------------------------------------------
    def test_approve_flow(self):
        line = self.env["bill.approval.user.line"].create({
            "move_id": self.bill.id,
            "user_id": self.approver.id,
        })
        line.action_send_request()
        self.assertEqual(line.state, "request")

        line.with_user(self.approver).action_approve()
        self.assertEqual(line.state, "done")
        self.assertTrue(line.date_approved)
        self.assertEqual(self.bill.bill_approval_state, "approved")

    def test_wrong_user_cannot_approve(self):
        line = self.env["bill.approval.user.line"].create({
            "move_id": self.bill.id,
            "user_id": self.approver.id,
            "state": "request",
        })
        with self.assertRaises(UserError):
            line.with_user(self.other_approver).action_approve()

    def test_reject_reopens_bill(self):
        """Väg B: rejecting puts the bill back into draft."""
        line = self.env["bill.approval.user.line"].create({
            "move_id": self.bill.id,
            "user_id": self.approver.id,
            "state": "done",
        })
        self.bill.action_post()
        self.assertEqual(self.bill.state, "posted")

        reject_line = self.env["bill.approval.user.line"].create({
            "move_id": self.bill.id,
            "user_id": self.other_approver.id,
            "state": "request",
        })
        reject_line.with_user(self.other_approver).action_reject(
            reason="Wrong amount"
        )
        self.assertEqual(reject_line.state, "rejected")
        self.assertEqual(reject_line.rejected_by_id, self.other_approver)
        self.assertEqual(reject_line.reject_reason, "Wrong amount")
        self.assertEqual(self.bill.state, "draft")

    def test_reject_requires_requested_state(self):
        line = self.env["bill.approval.user.line"].create({
            "move_id": self.bill.id,
            "user_id": self.approver.id,
            "state": "new",
        })
        with self.assertRaises(UserError):
            line.with_user(self.approver).action_reject(reason="nope")

    # ------------------------------------------------------------------
    # Multi-company
    # ------------------------------------------------------------------
    def test_company_id_is_filled(self):
        line = self.env["bill.approval.user.line"].create({
            "move_id": self.bill.id,
            "user_id": self.approver.id,
        })
        self.assertEqual(line.company_id, self.company)

    # ------------------------------------------------------------------
    # Systray
    # ------------------------------------------------------------------
    def test_systray_count(self):
        self.env["bill.approval.user.line"].create({
            "move_id": self.bill.id,
            "user_id": self.approver.id,
            "state": "request",
        })
        count = self.env["bill.approval.user.line"].with_user(
            self.approver
        ).ret_bill_approval_count()
        self.assertEqual(count, 1)

    # ------------------------------------------------------------------
    # Deletion guard
    # ------------------------------------------------------------------
    def test_approved_line_cannot_be_deleted(self):
        line = self.env["bill.approval.user.line"].create({
            "move_id": self.bill.id,
            "user_id": self.approver.id,
            "state": "done",
        })
        with self.assertRaises(ValidationError):
            line.unlink()
