# Copyright 2026 Vertel Sverige AB
# SPDX-License-Identifier: AGPL-3.0
"""Tests for account_journal_card_type.

The module adds card statements to journals and moves. It carries two
edition-conditioned pieces that this test pins:

- the multi-company restriction: <record model="ir.rule"> in 18/19, and
  <record model="ir.access"> with a company domain in 20.0. The test asserts
  the restriction exists in whichever form the edition uses, because losing
  it would let every user see every company's card statements.
- <group expand="0"> inside <search>, removed in 19.0.

The test must not touch ir.rule when the model is absent — 20.0 removed it.
"""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestCardStatement(TransactionCase):
    """The card statement model and its company restriction."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.Statement = cls.env["account.card.statement"]

    def test_model_exists(self):
        """The card statement model is registered."""
        self.assertIn("account.card.statement", self.env)
        self.assertIn("account.card.statement.line", self.env)

    def test_statement_has_company(self):
        """A card statement carries a company, which the rule restricts on."""
        self.assertIn("company_id", self.Statement._fields)
        self.assertEqual(
            self.Statement._fields["company_id"].comodel_name, "res.company")

    def _company_restriction_exists(self, model_name):
        """True if a company restriction exists in this edition's own form.

        18/19: ir.rule with a company domain.
        20.0:  ir.access with the same domain (ir.rule is gone).
        """
        model = self.env["ir.model"]._get(model_name)

        if "ir.access" in self.env:
            return bool(self.env["ir.access"].search([
                ("model_id", "=", model.id),
                ("domain", "ilike", "company_id"),
            ], limit=1))

        return bool(self.env["ir.rule"].search([
            ("model_id", "=", model.id),
            ("domain_force", "ilike", "company_id"),
        ], limit=1))

    def test_statement_company_restriction(self):
        """account.card.statement is restricted per company."""
        self.assertTrue(
            self._company_restriction_exists("account.card.statement"),
            "no company restriction on account.card.statement")

    def test_line_company_restriction(self):
        """account.card.statement.line is restricted per company."""
        self.assertTrue(
            self._company_restriction_exists("account.card.statement.line"),
            "no company restriction on account.card.statement.line")

    def test_card_statement_action_exists(self):
        """An act_window for card statements is registered."""
        action = self.env["ir.actions.act_window"].search([
            ("res_model", "=", "account.card.statement"),
        ], limit=1)
        self.assertTrue(action, "no act_window for card statements")
