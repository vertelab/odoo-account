# Copyright 2026 Vertel Sverige AB
# SPDX-License-Identifier: AGPL-3
"""Tests for account_analytic_replace.

The module lets one analytic account replace another and exposes the
replacement in ``name_search``. That override is the only place that touches
``odoo.osv`` — removed in 20.0 — so the tests exercise ``name_search`` with
and without arguments, which runs the edition-conditioned domain builder on
every edition.
"""
import inspect

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestAnalyticReplace(TransactionCase):
    """Replacement fields and the name_search override."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.plan = cls.env["account.analytic.plan"].search([], limit=1)
        if not cls.plan:
            cls.plan = cls.env["account.analytic.plan"].create({"name": "Test Plan"})
        cls.Account = cls.env["account.analytic.account"]
        cls.old = cls.Account.create({
            "name": "Old Analytic",
            "code": "OLD1",
            "plan_id": cls.plan.id,
            "company_id": cls.company.id,
        })
        cls.new = cls.Account.create({
            "name": "New Analytic",
            "code": "NEW1",
            "plan_id": cls.plan.id,
            "company_id": cls.company.id,
        })

    def test_replacement_fields_exist(self):
        """Both replacement fields are declared and point at the same model."""
        for name in ("replacement_account_id", "replaces_account_id"):
            self.assertIn(name, self.Account._fields, name)
            self.assertEqual(
                self.Account._fields[name].comodel_name,
                "account.analytic.account",
                name,
            )

    def test_link_replacement(self):
        """Linking old -> new is stored on both sides."""
        self.old.replacement_account_id = self.new
        self.new.replaces_account_id = self.old
        self.assertEqual(self.old.replacement_account_id, self.new)
        self.assertEqual(self.new.replaces_account_id, self.old)

    def test_name_search_without_name_delegates(self):
        """An empty name falls through to super() and does not build a domain."""
        results = self.Account.name_search(name="")
        self.assertIsInstance(results, list)

    def test_name_search_finds_by_name(self):
        """name_search matches the account's own name."""
        results = self.Account.name_search(name="Old Analytic", operator="ilike")
        ids = [rec[0] for rec in results]
        self.assertIn(self.old.id, ids)

    def test_name_search_finds_replaced_account(self):
        """name_search also matches through replaces_account_id.

        The domain is built with expression.AND in 18/19 and Domain.AND in
        20.0 — this is the line that would break if the condition were wrong.
        """
        self.new.replaces_account_id = self.old
        results = self.Account.name_search(name="Old Analytic", operator="ilike")
        ids = [rec[0] for rec in results]
        self.assertIn(self.new.id, ids,
                      "the replacing account should be found via its replacement")

    def _name_search(self, name, domain):
        """Call name_search with the keyword the edition uses.

        Odoo 19 renamed the args parameter to domain. The test has to
        follow, otherwise it pins the wrong signature.
        """
        if "domain" in inspect.signature(self.Account.name_search).parameters:
            return self.Account.name_search(name=name, domain=domain, operator="ilike")
        return self.Account.name_search(name=name, args=domain, operator="ilike")

    def test_name_search_with_args(self):
        """Passing args is ANDed with the name domain, not replacing it."""
        results = self._name_search("New Analytic", [("id", "=", self.new.id)])
        ids = [rec[0] for rec in results]
        self.assertEqual(ids, [self.new.id])

    def test_name_search_with_excluding_args(self):
        """An args filter that excludes the match returns nothing."""
        results = self._name_search("New Analytic", [("id", "!=", self.new.id)])
        ids = [rec[0] for rec in results]
        self.assertNotIn(self.new.id, ids)
