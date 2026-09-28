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
            # A reference is set so that SFA's ``supplier_reference_trigger``
            # does not intercept ``action_post`` with its confirmation
            # wizard (it returns an action instead of posting when the
            # vendor invoice number is missing).
            "ref": "TEST-INV-001",
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

    def test_post_guard_blocks_direct_post(self):
        """``_post()`` must be guarded too, not just ``action_post()``.

        The ``validate.account.move`` wizard (used by
        ``supplier_reference_trigger`` and Odoo's own abnormal checks) calls
        ``move_ids._post()`` directly, bypassing ``action_post`` entirely.
        """
        self.bill.approving_user_ids = [(0, 0, {"user_id": self.approver.id})]
        with self.assertRaises(ValidationError):
            self.bill._post()
        self.assertEqual(self.bill.state, "draft")

    def test_post_guard_blocks_validate_wizard(self):
        """Confirming the validate wizard must not skip the approval."""
        self.bill.approving_user_ids = [(0, 0, {"user_id": self.approver.id})]
        wizard = self.env["validate.account.move"].create({
            "move_ids": [(6, 0, self.bill.ids)],
        })
        with self.assertRaises(ValidationError):
            wizard.validate_move()
        self.assertEqual(self.bill.state, "draft")

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

    # ------------------------------------------------------------------
    # Request wizard (regression: it used to list every line in the DB)
    # ------------------------------------------------------------------
    def test_request_wizard_only_offers_own_lines(self):
        """The wizard must default to this bill's pending lines only."""
        own = self.env["bill.approval.user.line"].create({
            "move_id": self.bill.id,
            "user_id": self.approver.id,
        })
        # An unrelated bill with its own approver must not leak in.
        other_bill = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.vendor.id,
            "invoice_date": "2026-01-01",
            "ref": "TEST-INV-OTHER-1",
            "invoice_line_ids": [(0, 0, {
                "name": "Other line",
                "quantity": 1.0,
                "price_unit": 50.0,
                "account_id": self.env["account.account"].search(
                    [("account_type", "=", "expense")], limit=1
                ).id,
            })],
        })
        foreign = self.env["bill.approval.user.line"].create({
            "move_id": other_bill.id,
            "user_id": self.other_approver.id,
        })

        wizard = self.env["vendor.bill.approval.user"].create({
            "move_id": self.bill.id,
        })
        self.assertIn(own, wizard.line_ids)
        self.assertNotIn(
            foreign, wizard.line_ids,
            "The wizard must not offer another bill's approval lines.",
        )

    def test_request_wizard_rejects_foreign_lines(self):
        """A crafted RPC call must not send requests for another bill."""
        other_bill = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.vendor.id,
            "invoice_date": "2026-01-01",
            "ref": "TEST-INV-OTHER-2",
            "invoice_line_ids": [(0, 0, {
                "name": "Other line",
                "quantity": 1.0,
                "price_unit": 50.0,
                "account_id": self.env["account.account"].search(
                    [("account_type", "=", "expense")], limit=1
                ).id,
            })],
        })
        foreign = self.env["bill.approval.user.line"].create({
            "move_id": other_bill.id,
            "user_id": self.other_approver.id,
        })
        wizard = self.env["vendor.bill.approval.user"].create({
            "move_id": self.bill.id,
            "line_ids": [(6, 0, foreign.ids)],
        })
        with self.assertRaises(UserError):
            wizard.action_send()
        # The foreign line must be untouched.
        self.assertEqual(foreign.state, "new")

    def test_line_display_name_includes_state(self):
        line = self.env["bill.approval.user.line"].create({
            "move_id": self.bill.id,
            "user_id": self.approver.id,
            "state": "request",
        })
        self.assertIn(self.approver.name, line.display_name)
        self.assertIn("Requested", line.display_name)

    # ------------------------------------------------------------------
    # Access control: only Bill Approval / Manager configures approvers
    # ------------------------------------------------------------------
    def test_non_manager_cannot_add_approver(self):
        """A plain approver must not be able to add approvers."""
        with self.assertRaises(UserError):
            self.env["bill.approval.user.line"].with_user(
                self.approver
            ).create({
                "move_id": self.bill.id,
                "user_id": self.other_approver.id,
            })

    def test_non_manager_cannot_remove_approver(self):
        line = self.env["bill.approval.user.line"].create({
            "move_id": self.bill.id,
            "user_id": self.other_approver.id,
        })
        with self.assertRaises(UserError):
            line.with_user(self.approver).unlink()

    def test_non_manager_cannot_change_approver(self):
        line = self.env["bill.approval.user.line"].create({
            "move_id": self.bill.id,
            "user_id": self.approver.id,
        })
        with self.assertRaises(UserError):
            line.with_user(self.other_approver).write({
                "user_id": self.approver.id,
            })

    def test_approver_can_still_approve(self):
        """The state-only write done by approving must stay allowed."""
        line = self.env["bill.approval.user.line"].create({
            "move_id": self.bill.id,
            "user_id": self.approver.id,
            "state": "request",
        })
        line.with_user(self.approver).action_approve()
        self.assertEqual(line.state, "done")

    def test_approver_can_still_reject(self):
        line = self.env["bill.approval.user.line"].create({
            "move_id": self.bill.id,
            "user_id": self.approver.id,
            "state": "request",
        })
        line.with_user(self.approver).action_reject(reason="Nope")
        self.assertEqual(line.state, "rejected")

    def test_non_manager_cannot_set_vendor_defaults(self):
        with self.assertRaises(UserError):
            self.vendor.with_user(self.approver).write({
                "bill_approving_user_ids": [(6, 0, [self.approver.id])],
            })

    def test_manager_can_configure_approvers(self):
        manager = self.env["res.users"].create({
            "name": "Approval Manager",
            "login": "test_approval_manager",
            "email": "test_approval_manager@example.com",
            "company_id": self.company.id,
            "company_ids": [(6, 0, [self.company.id])],
            "groups_id": [(6, 0, [
                self.env.ref("base.group_user").id,
                self.env.ref("account.group_account_invoice").id,
                # Needed to write on res.partner in this test.
                self.env.ref("sales_team.group_sale_salesman").id,
                self.env.ref(
                    "account_bill_approval.group_bill_approval_manager"
                ).id,
            ])],
        })
        line = self.env["bill.approval.user.line"].with_user(
            manager
        ).create({
            "move_id": self.bill.id,
            "user_id": self.approver.id,
        })
        self.assertTrue(line)
        line.with_user(manager).unlink()
        self.vendor.with_user(manager).write({
            "bill_approving_user_ids": [(6, 0, [self.approver.id])],
        })
        self.assertIn(self.approver, self.vendor.bill_approving_user_ids)
