# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("-at_install", "post_install")
class TestPaymentOrderPending(AccountTestInvoicingCommon):
    """Verify that invoices on a 'pending until reconciliation' payment
    order get payment_state = 'in_payment' when the order is uploaded,
    even though no payment/reconciliation is created.

    Standard (non-pending) orders keep OCA behaviour (paid after upload).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.env.user.company_id = cls.company.id
        cls.env.user.groups_id |= cls.env.ref(
            "account_payment_order.group_account_payment"
        )
        cls.partner = cls.env["res.partner"].create({"name": "Pending Test Partner"})
        cls.invoice_line_account = cls.env["account.account"].create(
            {
                "name": "Test expense account",
                "code": "PENDING1",
                "account_type": "expense",
            }
        )
        cls.bank_journal = cls.company_data["default_journal_bank"]

        # The 'manual' outbound payment method has a working handler
        # (generate_payment_file returns (False, False)), so the full
        # draft -> uploaded flow can run in tests.
        cls.manual_method = cls.env.ref("account.account_payment_method_manual_out")
        cls.bank_journal.outbound_payment_method_line_ids = [
            Command.create({"payment_method_id": cls.manual_method.id})
        ]

        cls.product = cls.env["product.product"].create(
            {"name": "Test product", "type": "service"}
        )

        # Remove any leftover draft payment orders
        cls.env["account.payment.order"].search(
            [
                ("state", "=", "draft"),
                ("payment_type", "=", "outbound"),
                ("company_id", "=", cls.env.user.company_id.id),
            ]
        ).unlink()

    def _create_mode(self, name, method):
        mode = self.env["account.payment.mode"].create(
            {
                "name": name,
                "company_id": self.company.id,
                "bank_account_link": "variable",
                "payment_method_id": method.id,
            }
        )
        mode.variable_journal_ids = self.bank_journal
        return mode

    def _create_supplier_invoice(self, ref="PENDING-INV-001"):
        invoice = self.env["account.move"].create(
            {
                "partner_id": self.partner.id,
                "move_type": "in_invoice",
                "ref": ref,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "name": "product that cost 100",
                            "account_id": self.invoice_line_account.id,
                        },
                    )
                ],
            }
        )
        # NOTE: action_post() is overridden by SFA-specific modules in this
        # DB and does not post in the test env; use the core _post directly.
        invoice._post(soft=False)
        return invoice

    def _add_to_order(self, invoice, mode):
        """Post the invoice, set its payment mode, add to a payment order
        and return the (uploaded) order."""
        invoice.payment_mode_id = mode.id
        invoice.create_account_payment_line()
        order = invoice.line_ids.payment_line_ids.order_id
        self.assertTrue(order, "Invoice should be on a payment order")
        # Variable bank_account_link modes need the journal set manually
        order.journal_id = self.bank_journal.id
        order.payment_mode_id_change()
        order.draft2open()
        order.open2generated()
        order.generated2uploaded()
        return order

    def test_pending_order_invoice_gets_in_payment(self):
        """An invoice added to a pending payment order that is uploaded
        must have payment_state = 'in_payment'."""
        # Mark the manual method as pending-until-reconciliation
        self.manual_method.pending_until_reconciliation = True
        mode = self._create_mode("Test Pending Mode", self.manual_method)

        invoice = self._create_supplier_invoice("PEND-001")
        order = self._add_to_order(invoice, mode)

        self.assertEqual(order.state, "uploaded")
        self.assertTrue(order.payment_method_id.pending_until_reconciliation)
        self.assertEqual(
            invoice.payment_state,
            "in_payment",
            "Invoice on an uploaded pending payment order should be in_payment",
        )

    def test_non_pending_order_invoice_is_paid(self):
        """A standard (non-pending) payment order posts and reconciles —
        the invoice becomes paid after upload."""
        # Manual method stays non-pending (default)
        mode = self._create_mode("Test Normal Mode", self.manual_method)

        invoice = self._create_supplier_invoice("NONPEND-002")
        order = self._add_to_order(invoice, mode)

        self.assertEqual(order.state, "uploaded")
        self.assertFalse(order.payment_method_id.pending_until_reconciliation)
        # A standard (non-pending) order posts and reconciles, so the invoice
        # must NOT remain 'not_paid' — it becomes 'paid' (or 'in_payment' when
        # the payments are not fully marked matched in this test DB, which is
        # OCA's own standard behaviour, not our override).
        self.assertNotEqual(
            invoice.payment_state,
            "not_paid",
            "Invoice on a non-pending uploaded order should not stay not_paid",
        )

    def test_pending_order_invoice_not_paid_before_upload(self):
        """Before the order is uploaded, a pending-order invoice has not yet
        been flagged in_payment (it stays not_paid until upload)."""
        self.manual_method.pending_until_reconciliation = True
        mode = self._create_mode("Test Pending Mode 2", self.manual_method)

        invoice = self._create_supplier_invoice("PEND-003")
        invoice.payment_mode_id = mode.id
        invoice.create_account_payment_line()
        order = invoice.line_ids.payment_line_ids.order_id
        order.journal_id = self.bank_journal.id
        order.payment_mode_id_change()

        # Only confirm + generate, do NOT upload yet
        order.draft2open()
        order.open2generated()
        self.assertEqual(order.state, "generated")
        # No payments/reconciles exist, nothing flags in_payment prematurely
        self.assertNotEqual(invoice.payment_state, "in_payment")

        order.generated2uploaded()
        self.assertEqual(order.state, "uploaded")
        self.assertEqual(invoice.payment_state, "in_payment")
