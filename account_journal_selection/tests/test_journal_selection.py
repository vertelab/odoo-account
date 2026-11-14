# Copyright 2026 Vertel Sverige AB
# SPDX-License-Identifier: AGPL-3
"""Tests for account_journal_selection.

The module adds four account fields to ``account.journal`` and a constraint
that warns when a sale/purchase journal's default account is a receivable or
payable. The constraint is a warning, not a ValidationError — the test pins
that behaviour so a future change to raise does not go unnoticed.
"""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestJournalSelection(TransactionCase):
    """The four account fields and the type constraint."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.journal = cls.env["account.journal"].search([
            ("type", "=", "sale"),
            ("company_id", "=", cls.company.id),
        ], limit=1)
        if not cls.journal:
            cls.journal = cls.env["account.journal"].create({
                "name": "Test Sale Journal",
                "code": "TSJ",
                "type": "sale",
                "company_id": cls.company.id,
            })

    def test_fields_exist(self):
        """All four fields are declared on account.journal."""
        self.assertIn("default_account_id", self.journal._fields)
        self.assertIn("payment_debit_account_id", self.journal._fields)
        self.assertIn("payment_credit_account_id", self.journal._fields)
        self.assertIn("suspense_account_id", self.journal._fields)

    def test_fields_are_account_account(self):
        """Each field points at account.account and is company-checked."""
        for name in (
            "default_account_id",
            "payment_debit_account_id",
            "payment_credit_account_id",
            "suspense_account_id",
        ):
            field = self.journal._fields[name]
            self.assertEqual(field.comodel_name, "account.account", name)
            self.assertTrue(field.check_company, name)

    def test_default_account_can_be_set(self):
        """Setting default_account_id persists."""
        account = self.env["account.account"].search([
            ("company_ids", "in", self.company.id),
            ("account_type", "=", "expense"),
        ], limit=1)
        if not account:
            self.skipTest("no expense account in the test chart")
        self.journal.default_account_id = account
        self.assertEqual(self.journal.default_account_id, account)

    def test_constraint_does_not_raise_on_receivable(self):
        """The receivable/payable check logs a warning, it does not raise.

        Pinning this keeps a future 'raise ValidationError' visible: it would
        break every existing journal whose default account is a receivable.
        """
        receivable = self.env["account.account"].search([
            ("company_ids", "in", self.company.id),
            ("account_type", "=", "asset_receivable"),
        ], limit=1)
        if not receivable:
            self.skipTest("no receivable account in the test chart")
        # Must not raise.
        self.journal.write({"default_account_id": receivable.id})
        self.assertEqual(self.journal.default_account_id, receivable)
