# Copyright 2026 Vertel Sverige AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
"""Tests for account_tagetik.

The module adds the Tagetik reporting fields to accounts and journal items.
The field names are a contract: account_account.tagetik_code/tagetik_text
already exist as columns in production, and the module only replaces the
Linserv module that declared them. Renaming a field would therefore orphan
the stored values, so the names are pinned here.

The related fields on account.move.line are stored: they copy the account's
value onto the line at write time and must be refreshed when the account
changes. account.move reads through to its lines and is not stored.
"""

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

TAGETIK_FIELD_NAMES = ("tagetik_code", "tagetik_text")


@tagged("post_install", "-at_install")
class TestTagetikFields(AccountTestInvoicingCommon):
    """The Tagetik fields exist, keep their names, and propagate to lines."""

    @classmethod
    def get_default_groups(cls):
        """Add the groups this database requires to create res.partner.

        AccountTestInvoicingCommon.setUpClass() builds its test user from
        get_default_groups() and then creates an independent company, which
        creates a partner. On databases where contact creation is restricted
        to Contact Creation / Sales / Purchase / Inventory administrators,
        that create raises AccessError before any test runs. Adding the groups
        afterwards is too late.
        """
        groups = super().get_default_groups()
        return groups | cls.env.ref("base.group_partner_manager")

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
            # sfa_core is a customer module and is not present in every
            # database. Without it the model does not exist at all, so the
            # lookup must be guarded — otherwise setUpClass fails with
            # KeyError before any test runs.
            if "product.category.type" in env:
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
        cls.account = cls.company_data["default_account_revenue"]
        cls.account.write({
            "tagetik_code": "301000",
            "tagetik_text": "Tagetik revenue",
        })

    def _create_move(self, account, **line_values):
        """Post-free journal entry with one line on the given account."""
        return self.env["account.move"].create({
            "move_type": "entry",
            "line_ids": [
                Command.create(dict(
                    {"account_id": account.id, "balance": 100.0},
                    **line_values,
                )),
                Command.create({"account_id": self.company_data["default_account_expense"].id,
                                "balance": -100.0}),
            ],
        })

    def test_fields_exist_on_account(self):
        """account.account carries both fields."""
        for name in TAGETIK_FIELD_NAMES:
            self.assertIn(name, self.env["account.account"]._fields)

    def test_fields_exist_on_move(self):
        """account.move carries both fields, unstored."""
        for name in TAGETIK_FIELD_NAMES:
            field = self.env["account.move"]._fields[name]
            self.assertFalse(field.store)
            self.assertEqual(field.related, "line_ids.account_id.%s" % name)

    def test_fields_exist_on_move_line(self):
        """account.move.line carries both fields, stored and related."""
        for name in TAGETIK_FIELD_NAMES:
            field = self.env["account.move.line"]._fields[name]
            self.assertTrue(field.store)
            self.assertEqual(field.related, "account_id.%s" % name)

    def test_fields_exist_on_bank_statement_line(self):
        """account.bank.statement.line carries both fields."""
        for name in TAGETIK_FIELD_NAMES:
            self.assertIn(name, self.env["account.bank.statement.line"]._fields)

    def test_account_fields_are_not_copied(self):
        """A copied account starts without Tagetik values."""
        copied = self.account.copy()
        self.assertFalse(copied.tagetik_code)
        self.assertFalse(copied.tagetik_text)

    def test_move_line_gets_account_values(self):
        """A new line copies code and text from its account."""
        move = self._create_move(self.account)
        line = move.line_ids.filtered(lambda l: l.account_id == self.account)
        self.assertEqual(line.tagetik_code, "301000")
        self.assertEqual(line.tagetik_text, "Tagetik revenue")

    def test_move_line_follows_account_update(self):
        """Changing the account refreshes the stored line values."""
        move = self._create_move(self.account)
        self.account.write({
            "tagetik_code": "301100",
            "tagetik_text": "Tagetik revenue updated",
        })
        line = move.line_ids.filtered(lambda l: l.account_id == self.account)
        self.assertEqual(line.tagetik_code, "301100")
        self.assertEqual(line.tagetik_text, "Tagetik revenue updated")

    def test_move_line_follows_account_change(self):
        """Pointing the line at another account refreshes the stored values."""
        other_account = self.copy_account(
            self.company_data["default_account_revenue"],
            {"tagetik_code": "302000", "tagetik_text": "Other revenue"},
        )
        move = self._create_move(self.account)
        line = move.line_ids.filtered(lambda l: l.account_id == self.account)
        line.account_id = other_account
        self.assertEqual(line.tagetik_code, "302000")
        self.assertEqual(line.tagetik_text, "Other revenue")

    def test_move_reads_values_through_lines(self):
        """The unstored move field reads the value from its lines."""
        move = self._create_move(self.account)
        self.assertEqual(move.tagetik_code, "301000")
        self.assertEqual(move.tagetik_text, "Tagetik revenue")

    def test_move_line_is_searchable_on_tagetik_code(self):
        """The stored line field can be searched on."""
        move = self._create_move(self.account)
        found = self.env["account.move.line"].search([
            ("id", "in", move.line_ids.ids),
            ("tagetik_code", "=", "301000"),
        ])
        self.assertEqual(len(found), 1)
