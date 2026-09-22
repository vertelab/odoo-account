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
    def get_default_groups(cls):
        """Extend the account test defaults with the groups this database
        requires for res.company / res.partner creation.

        AccountTestInvoicingCommon.setUpClass() switches cls.env to the
        'accountman' test user (built from get_default_groups) and then creates
        an independent test company. That creation is restricted to
        Administration/Access Rights here, so the test user must carry those
        groups from the start — adding them after super().setUpClass() is too
        late, the AccessError has already been raised.
        """
        groups = super().get_default_groups()
        return groups | cls.env.ref("base.group_erp_manager") | cls.env.ref(
            "base.group_partner_manager"
        )

    @classmethod
    def setUpClass(cls):
        # sfa_core makes product.category.category_type_id required (NOT NULL
        # at the database level). ProductCommon.setUpClass() creates
        # 'Test Category' without it, which raises NotNullViolation. The
        # constraint is an SFA business rule, not something this module's tests
        # exercise, so a default type is injected into every product.category
        # create for the duration of the test class.
        from odoo import SUPERUSER_ID, api
        from odoo import registry as registry_module
        from odoo.tests.common import get_db_name

        categ_type_id = False
        with registry_module(get_db_name()).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            categ_type_id = env["product.category.type"].search([], limit=1).id

        if categ_type_id:
            ProductCategory = registry_module(get_db_name())["product.category"]
            orig_create = ProductCategory.create

            @api.model_create_multi
            def create(self, vals_list):
                for vals in vals_list:
                    vals.setdefault("category_type_id", categ_type_id)
                return orig_create(self, vals_list)

            cls.classPatch(ProductCategory, "create", create)

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

    def _autogiro_mode(self):
        """An Autogiro payment mode in the test company.

        The module's data mode belongs to base.main_company, but
        AccountTestInvoicingCommon runs in an independent company, so a
        company-local mode is needed to link it to a bill.
        """
        mode = self.env["account.payment.mode"].search(
            [
                ("payment_method_id", "=", self.autogiro_method.id),
                ("company_id", "=", self.company.id),
            ],
            limit=1,
        )
        if not mode:
            mode = self.env["account.payment.mode"].create(
                {
                    "name": "Autogiro (test)",
                    "company_id": self.company.id,
                    "bank_account_link": "variable",
                    "payment_method_id": self.autogiro_method.id,
                }
            )
            mode.variable_journal_ids = self.bank_journal
        return mode

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
        """Req 1: confirming Pay with Autogiro leaves the invoice in_payment
        (Pågående) and creates nothing — no payment, no journal entry. The bank
        transaction settles the bill later."""
        invoice = self._create_supplier_invoice("AUTOGIRO-001")
        wizard = self._open_pay_wizard(invoice)

        # The accountant selects the Autogiro method for this vendor bill.
        autogiro_line = wizard.available_payment_method_line_ids.filtered(
            lambda line: line.payment_method_id == self.autogiro_method
        )[:1]
        if autogiro_line:
            wizard.payment_method_line_id = autogiro_line

        # The decision helper must treat this as an Autogiro pending pay.
        self.assertTrue(self.autogiro_method.pending_until_reconciliation)
        self.assertTrue(wizard._is_autogiro_pending_pay())

        # Confirm: creates + posts the payment but skips reconciliation.
        res = wizard.action_create_payments()

        # The invoice must read in_payment (not paid/not_paid).
        invoice.invalidate_recordset(["payment_state"])
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

        # No payment and no journal entry are created at all: the bank
        # transaction settles the bill, so there is nothing for a payment to
        # book. The bill carries the flag instead.
        self.assertTrue(
            invoice.is_pending_bank,
            "The bill must be flagged as awaiting bank settlement",
        )
        self.assertFalse(
            invoice.matched_payment_ids,
            "The invoice must not be reconciled with a payment yet",
        )
        self.assertFalse(
            self.env["account.payment"].search(
                [("partner_id", "=", self.partner.id)]
            ),
            "Autogiro confirm must not create a payment",
        )

    def test_reconciliation_to_paid_clears_pending_signal(self):
        """Req 1 scenario 2: a settle (residual reaches zero / derived paid)
        flips the invoice to 'paid' and clears the pending flag."""
        invoice = self._create_supplier_invoice("AUTOGIRO-002")
        invoice.write({"is_pending_bank": True})
        invoice._compute_payment_state()
        self.assertEqual(invoice.payment_state, "in_payment")

        # Simulate the bank settling the bill: book the outflow against the
        # payable account and reconcile it, so core derives 'paid'. The
        # override must not fight it, and must clear the flag.
        payable_lines = invoice.line_ids.filtered(
            lambda line: line.account_id.account_type == "liability_payable"
            and not line.reconciled
        )
        amount = abs(sum(payable_lines.mapped("amount_residual")))
        settlement = self.env["account.move"].create(
            {
                "journal_id": self.bank_journal.id,
                "date": fields.Date.today(),
                "ref": invoice.name or "bank settlement",
                "line_ids": [
                    Command.create(
                        {
                            "name": invoice.name or "bank settlement",
                            "account_id": payable_lines.account_id.id,
                            "debit": amount,
                            "credit": 0.0,
                            "partner_id": invoice.commercial_partner_id.id,
                        }
                    ),
                    Command.create(
                        {
                            "name": invoice.name or "bank settlement",
                            "account_id": self.bank_journal.default_account_id.id,
                            "debit": 0.0,
                            "credit": amount,
                            "partner_id": invoice.commercial_partner_id.id,
                        }
                    ),
                ],
            }
        )
        settlement._post(soft=False)
        counterpart = settlement.line_ids.filtered(
            lambda line: line.account_id == payable_lines.account_id
        )
        (payable_lines + counterpart).reconcile()

        invoice._compute_payment_state()
        self.assertEqual(invoice.payment_state, "paid")
        self.assertFalse(
            invoice.is_pending_bank,
            "The pending flag must clear once the bill is paid",
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
        mode = self._autogiro_mode()
        invoice = self._create_supplier_invoice("AUTOGIRO-004", mode=mode)
        self.assertTrue(invoice.is_autogiro_vendor_bill)

    def test_wizard_preselects_autogiro_for_autogiro_bill(self):
        """Req 2: opening the Pay wizard on an Autogiro bill pre-selects the
        Autogiro method, without the accountant having to choose it."""
        mode = self._autogiro_mode()
        invoice = self._create_supplier_invoice("AUTOGIRO-005", mode=mode)
        self.assertTrue(invoice.is_autogiro_vendor_bill)

        wizard = self._open_pay_wizard(invoice)

        self.assertEqual(
            wizard.payment_method_line_id.payment_method_id,
            self.autogiro_method,
            "The wizard must pre-select Autogiro for an Autogiro vendor bill",
        )

    def test_wizard_does_not_preselect_autogiro_for_other_bills(self):
        """Req 2: a bill that is not an Autogiro bill must not be defaulted."""
        invoice = self._create_supplier_invoice("AUTOGIRO-006")
        self.assertFalse(invoice.is_autogiro_vendor_bill)

        wizard = self._open_pay_wizard(invoice)

        self.assertNotEqual(
            wizard.payment_method_line_id.payment_method_id,
            self.autogiro_method,
            "A non-Autogiro bill must not be defaulted to Autogiro",
        )

    def test_manually_selected_autogiro_also_stays_pending(self):
        """Req 1: the decision is based on the selected method, so an invoice
        without an Autogiro payment mode still stays in_payment when the
        accountant picks Autogiro by hand."""
        invoice = self._create_supplier_invoice("AUTOGIRO-007")
        wizard = self._open_pay_wizard(invoice)
        autogiro_line = wizard.available_payment_method_line_ids.filtered(
            lambda line: line.payment_method_id == self.autogiro_method
        )[:1]
        self.assertTrue(autogiro_line, "Sanity: the journal offers Autogiro")
        wizard.payment_method_line_id = autogiro_line

        wizard.action_create_payments()

        invoice.invalidate_recordset(["payment_state"])
        self.assertEqual(invoice.payment_state, "in_payment")
        self.assertTrue(invoice.is_pending_bank)
