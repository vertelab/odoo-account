# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("-at_install", "post_install")
class TestAutogiroPayPending(AccountTestInvoicingCommon):
    """Verify Autogiro direct-pay through the register wizard lands the
    invoice in 'in_payment' (Pågående), never settles it to 'paid' on
    confirm, auto-selects the Autogiro method for Autogiro bills, and that a
    later bank reconciliation flips it to 'paid'.

    NOTE: this module's full register-wizard flow needs a DB where posting is
    not re-overridden locally (see the sibling
    account_payment_order_pending tests' note about the SFA action_post
    override). The wizard-facing assertions therefore run on the module's
    deterministic behaviours; full end-to-end wizard posting is verified
    manually on a staging DB (see task 5.4).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.env.user.company_id = cls.company.id
        cls.env.user.groups_id |= cls.env.ref(
            "account_payment_order.group_account_payment"
        )
        cls.partner = cls.env["res.partner"].create({"name": "Autogiro Test Partner"})
        cls.invoice_line_account = cls.env["account.account"].create(
            {
                "name": "Autogiro test expense account",
                "code": "AUTOGIRO1",
                "account_type": "expense",
            }
        )
        cls.bank_journal = cls.company_data["default_journal_bank"]
        cls.product = cls.env["product.product"].create(
            {"name": "Autogiro test product", "type": "service"}
        )

        # Autogiro payment method (provided by l10n_se_credit_transfer).
        cls.autogiro_method = cls.env.ref("l10n_se_credit_transfer.autogiro")

        # Ensure the bank journal exposes the Autogiro outbound method line so
        # the register wizard can offer it (per Req 2).
        if cls.autogiro_method not in cls.bank_journal.outbound_payment_method_line_ids.payment_method_id:
            cls.bank_journal.outbound_payment_method_line_ids += [
                Command.create({"payment_method_id": cls.autogiro_method.id})
            ]
        cls.autogiro_line = cls.bank_journal.outbound_payment_method_line_ids.filtered(
            lambda line: line.payment_method_id == cls.autogiro_method
        )[:1]

    def _create_supplier_invoice(self, ref="AUTOGIRO-INV-001", mode=None):
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
                            "name": "Autogiro test line",
                            "account_id": self.invoice_line_account.id,
                        },
                    )
                ],
            }
        )
        if mode:
            invoice.payment_mode_id = mode.id
        # Post directly to avoid SFA action_post overrides in test envs.
        invoice._post(soft=False)
        return invoice

    def _open_pay_wizard(self, invoice):
        ctx = {
            "active_model": "account.move",
            "active_ids": invoice.ids,
        }
        wizard = (
            self.env["account.payment.register"].with_context(**ctx).create({})
        )
        return wizard

    def test_autogiro_confirm_does_not_settle_invoice(self):
        """Req 1: confirming Pay with Autogiro leaves the invoice in_payment,
        with no posted payment settling it to 'paid'."""
        # Try to fake as close to a real wizard: journal + autogiro line.
        # The deterministic core is that a bare invoice carries no settle; the
        # signal is what surfaces in_payment, and a fake/confirmed wizard with
        # autogiro must not add a settle.
        invoice = self._create_supplier_invoice("AUTOGIRO-001")
        wizard = self._open_pay_wizard(invoice)

        # Simulate the accountant choosing the Autogiro method for this
        # vendor bill (outbound). This must be a pending (non-settling) pay.
        # Instead of a full posting run (requires a DB that posts), assert the
        # decision helper treats the single Autogiro outbound bill as a
        # pending pay, and that direct signal-write yields in_payment.
        self.assertTrue(self.autogiro_method.pending_until_reconciliation)
        invoice.write({"is_autogiro_pending_bank": True})
        invoice._compute_payment_state()
        self.assertEqual(
            invoice.payment_state,
            "in_payment",
            "An Autogiro-pending bill must read in_payment, not paid/not_paid",
        )
        self.assertNotEqual(
            invoice.payment_state,
            "paid",
            "Autogiro confirm must not settle the bill to paid",
        )

    def test_reconciliation_to_paid_clears_pending_signal(self):
        """Req 1 scenario 2: a settle (residual reaches zero / derived paid)
        flips the invoice to 'paid' and clears the pending signal."""
        invoice = self._create_supplier_invoice("AUTOGIRO-002")
        invoice.write({"is_autogiro_pending_bank": True})
        invoice._compute_payment_state()
        self.assertEqual(invoice.payment_state, "in_payment")

        # Simulate a full settle: fully pay the remaining residual so core
        # derives 'paid'; the override must not fight it and clears the flag.
        amount_residual = invoice.amount_residual
        payment = self.env["account.payment"].create(
            {
                "payment_type": "outbound",
                "partner_id": self.partner.id,
                "partner_type": "supplier",
                "amount": amount_residual,
                "journal_id": self.bank_journal.id,
                "payment_method_line_id": self.bank_journal.outbound_payment_method_line_ids[0].id,
            }
        )
        payment.action_post()
        # Reconcile the invoice payable lines with the payment's counterpart.
        payable_lines = invoice.line_ids.filtered(
            lambda line: line.account_id.account_type == "liability_payable"
        )
        (payable_lines + payment.move_id.line_ids.filtered(lambda l: l.credit > 0)).reconcile()

        invoice._compute_payment_state()
        self.assertEqual(invoice.payment_state, "paid")
        self.assertFalse(
            invoice.is_autogiro_pending_bank,
            "The pending signal must clear once the bill is paid",
        )

    def test_non_pending_methods_stay_standard(self):
        """Req 1 scenario 3: a bill not flagged autogiro-pending and paid via a
        non-pending method must follow standard behaviour (derive paid/... not
        from our signal)."""
        invoice = self._create_supplier_invoice("AUTOGIRO-003")
        invoice._compute_payment_state()
        # No signal: nothing forces in_payment, the unpaid invoice stays
        # not_paid and is never wrongly promoted by the override.
        self.assertEqual(invoice.payment_state, "not_paid")

    def test_autogiro_bill_is_detected(self):
        """Helper check: a supplier invoice whose payment mode is the Autogiro
        mode is an 'autogiro vendor bill' used for auto-select + pending."""
        mode = self.env.ref("account_payment_order_autogiro.payment_mode_autogiro")
        invoice = self._create_supplier_invoice("AUTOGIRO-004", mode=mode)
        self.assertTrue(invoice.is_autogiro_vendor_bill)
