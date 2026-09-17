# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("-at_install", "post_install")
class TestPaymentOrderPending(AccountTestInvoicingCommon):
    """Verify the four requirements of a 'pending until reconciliation' order:

    1. A bill linked to a payment order reads 'in_payment' from the moment it
       is linked — not only once the order is uploaded.
    2. The bill becomes 'paid' when the bank transaction is reconciled
       against it.
    3. The payment follows the bill: it is booked and becomes 'paid' at that
       same moment.
    4. No journal entry is created for the payments while the order is merely
       uploaded: nothing may be booked before the bank confirms the movement.

    Standard (non-pending) orders keep OCA behaviour: posted and reconciled
    at upload time.
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

        # The automatic reconciliation of account_reconcile_oca relies on
        # account.reconcile.model rules. The demo rules live on the main
        # company, so an equivalent rule is created for the test company.
        cls.reconcile_model = cls.env["account.reconcile.model"].create(
            {
                "name": "Test Invoices/Bills Perfect Match",
                "rule_type": "invoice_matching",
                "company_id": cls.company.id,
                "auto_reconcile": True,
            }
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

    def _add_to_order(self, invoice, mode, upload=True):
        """Link the invoice to a payment order and optionally upload it."""
        invoice.payment_mode_id = mode.id
        invoice.create_account_payment_line()
        order = invoice.line_ids.payment_line_ids.order_id
        self.assertTrue(order, "Invoice should be on a payment order")
        # Variable bank_account_link modes need the journal set manually
        order.journal_id = self.bank_journal.id
        order.payment_mode_id_change()
        order.draft2open()
        order.open2generated()
        if upload:
            order.generated2uploaded()
        return order

    def _reconcile_bank_transaction(self, invoice, amount):
        """Create a bank transaction for the invoice and reconcile it, the way
        the bank reconciliation widget does.

        The reconciliation models (account.reconcile.model, rule_type
        'invoice_matching') match the transaction against the bill
automatically on create. account_reconcile_oca skips that step in test
        mode unless this context flag is set, so it is passed explicitly —
        otherwise the test would exercise a flow that never happens in
        production.
        """
        st_line = (
            self.env["account.bank.statement.line"]
            .with_context(_test_account_reconcile_oca=True)
            .create(
                {
                    "journal_id": self.bank_journal.id,
                    "date": fields.Date.today(),
                    "payment_ref": invoice.name or "bank transaction",
                    "amount": -amount,
                    "partner_id": invoice.commercial_partner_id.id,
                }
            )
        )
        if st_line.is_reconciled:
            return st_line

        payable = invoice.line_ids.filtered(
            lambda line: line.account_id.account_type == "liability_payable"
            and not line.reconciled
        )
        counterpart = st_line.move_id.line_ids.filtered(
            lambda line: line.account_id == payable.account_id
            and not line.reconciled
        )
        if payable and counterpart:
            (payable + counterpart).reconcile()
        return st_line

    # ------------------------------------------------------------------
    # Requirement 1 — in_payment from the moment the bill is linked
    # ------------------------------------------------------------------

    def test_linked_invoice_is_in_payment_before_upload(self):
        """A bill linked to a pending order reads 'in_payment' immediately,
        before the order is uploaded."""
        self.manual_method.pending_until_reconciliation = True
        mode = self._create_mode("Test Pending Linked", self.manual_method)

        invoice = self._create_supplier_invoice("PEND-LINKED-001")
        order = self._add_to_order(invoice, mode, upload=False)
        self.assertEqual(order.state, "generated")

        invoice._compute_payment_state()
        self.assertEqual(
            invoice.payment_state,
            "in_payment",
            "A bill linked to a pending order must be in_payment immediately",
        )

    def test_unlinked_invoice_is_not_paid(self):
        """A bill not linked to anything keeps the standard state."""
        invoice = self._create_supplier_invoice("PEND-UNLINKED-001")
        self.assertEqual(invoice.payment_state, "not_paid")

    # ------------------------------------------------------------------
    # Requirement 4 — no journal entry while merely uploaded
    # ------------------------------------------------------------------

    def test_uploaded_pending_order_creates_no_journal_entry(self):
        """Uploading a pending order must not book anything."""
        self.manual_method.pending_until_reconciliation = True
        mode = self._create_mode("Test Pending NoJE", self.manual_method)

        invoice = self._create_supplier_invoice("PEND-NOJE-001")
        order = self._add_to_order(invoice, mode)

        self.assertEqual(order.state, "uploaded")
        self.assertTrue(order.payment_ids, "Pending order should have payments")
        for payment in order.payment_ids:
            self.assertFalse(
                payment.move_id,
                "A pending order must not create a journal entry at upload",
            )
            self.assertEqual(
                payment.state,
                "draft",
                "Pending-order payments must stay in draft at upload",
            )
        self.assertEqual(invoice.payment_state, "in_payment")
        self.assertFalse(
            invoice.matched_payment_ids,
            "The bill must not be reconciled yet",
        )

    # ------------------------------------------------------------------
    # Requirements 2 and 3 — paid at bank reconciliation, payment follows
    # ------------------------------------------------------------------

    def test_bank_reconciliation_settles_bill_and_payment(self):
        """Reconciling the bank transaction settles the bill and books the
        payment, which then follows the bill to 'paid'."""
        self.manual_method.pending_until_reconciliation = True
        mode = self._create_mode("Test Pending Settled", self.manual_method)

        invoice = self._create_supplier_invoice("PEND-SETTLED-001")
        order = self._add_to_order(invoice, mode)
        payment = order.payment_ids
        self.assertFalse(payment.move_id, "Sanity: nothing booked yet")

        self._reconcile_bank_transaction(invoice, payment.amount)

        self.assertTrue(
            invoice.currency_id.is_zero(invoice.amount_residual),
            "Sanity: the bill must be fully reconciled",
        )
        self.assertEqual(
            invoice.payment_state,
            "paid",
            "A bill settled against the bank must be paid",
        )
        self.assertTrue(
            payment.move_id,
            "The payment must be booked once the bank confirms the movement",
        )
        self.assertEqual(
            payment.state,
            "paid",
            "The payment must follow the bill to paid",
        )

    def test_payment_not_booked_before_bank_confirmation(self):
        """The journal entry appears only at bank reconciliation, never at
        upload."""
        self.manual_method.pending_until_reconciliation = True
        mode = self._create_mode("Test Pending Timing", self.manual_method)

        invoice = self._create_supplier_invoice("PEND-TIMING-001")
        order = self._add_to_order(invoice, mode)
        payment = order.payment_ids

        self.assertFalse(payment.move_id, "No journal entry at upload")
        self._reconcile_bank_transaction(invoice, payment.amount)
        self.assertTrue(payment.move_id, "Journal entry created at reconcile")

    # ------------------------------------------------------------------
    # Standard (non-pending) behaviour must be untouched
    # ------------------------------------------------------------------

    def test_non_pending_order_posts_and_reconciles(self):
        """A standard order keeps OCA behaviour: posted and reconciled."""
        mode = self._create_mode("Test Normal Mode", self.manual_method)

        invoice = self._create_supplier_invoice("NONPEND-002")
        order = self._add_to_order(invoice, mode)

        self.assertEqual(order.state, "uploaded")
        self.assertFalse(order.payment_method_id.pending_until_reconciliation)
        self.assertTrue(
            all(p.move_id for p in order.payment_ids),
            "A standard order must book its payments at upload",
        )
        self.assertNotEqual(
            invoice.payment_state,
            "not_paid",
            "A standard order must not leave the bill unpaid",
        )
