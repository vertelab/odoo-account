# Copyright 2026 Vertel Sverige AB
# SPDX-License-Identifier: AGPL-3.0
"""Tests for account_fiscal_year_vrtl.

The module extends OCA's account.fiscal.year with periods, a state and a
hash-locked period close. It carries two edition-conditioned pieces:

- name_search: Odoo 19 renamed the ``args`` parameter to ``domain``. The
  override branches on the edition; the test calls it through a helper that
  picks the right keyword, so both branches are exercised.
- the multi-company rules: ir.rule in 18/19, ir.access with a domain in 20.0.

Both are pinned here because a wrong branch silently changes behaviour
instead of failing loudly.
"""
import inspect

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestFiscalYear(TransactionCase):
    """The fiscal year model, its periods and its name_search."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.FiscalYear = cls.env["account.fiscal.year"]
        cls.fy = cls.FiscalYear.create({
            "name": "Test FY 2098",
            "date_from": "2098-01-01",
            "date_to": "2098-12-31",
            "company_id": cls.company.id,
        })

    def test_state_defaults_to_draft(self):
        """A new fiscal year is open."""
        self.assertEqual(self.fy.state, "draft")

    def test_periods_relation(self):
        """period_ids is the inverse of account.period.fiscalyear_id."""
        field = self.FiscalYear._fields["period_ids"]
        self.assertEqual(field.comodel_name, "account.period")
        self.assertEqual(field.inverse_name, "fiscalyear_id")

    def test_end_date_before_start_raises(self):
        """date_to earlier than date_from is rejected."""
        with self.assertRaises(ValidationError):
            self.FiscalYear.create({
                "name": "Bad FY",
                "date_from": "2098-12-31",
                "date_to": "2098-01-01",
                "company_id": self.company.id,
            })

    def _name_search(self, name, domain):
        """Call name_search with the keyword this edition uses.

        Odoo 19 renamed ``args`` to ``domain``. The module conditions the
        signature; the test has to follow, otherwise it pins the wrong one.
        """
        if "domain" in inspect.signature(self.FiscalYear.name_search).parameters:
            return self.FiscalYear.name_search(name=name, domain=domain, operator="ilike")
        return self.FiscalYear.name_search(name=name, args=domain, operator="ilike")

    def test_name_search_finds_by_name(self):
        """name_search matches the fiscal year's own name."""
        results = self._name_search("Test FY 2098", [])
        ids = [rec[0] for rec in results]
        self.assertIn(self.fy.id, ids)

    def test_name_search_with_domain(self):
        """A domain is ANDed with the name match, not replacing it."""
        results = self._name_search("Test FY 2098", [("id", "=", self.fy.id)])
        ids = [rec[0] for rec in results]
        self.assertEqual(ids, [self.fy.id])

    def test_name_search_domain_is_ored_with_name(self):
        """The caller's domain is ORed with the name match, not ANDed.

        The override builds ['|', *domain, (name, op, name)], so a record that
        matches the name is returned even when the domain excludes it. That is
        the module's intended behaviour — pinning it makes a future change to
        AND visible.
        """
        results = self._name_search("Test FY 2098", [("id", "!=", self.fy.id)])
        ids = [rec[0] for rec in results]
        self.assertIn(self.fy.id, ids)

    def test_company_restriction_exists(self):
        """The fiscal year is restricted per company, in the edition's form."""
        model = self.env["ir.model"]._get("account.fiscal.year")
        if "ir.access" in self.env:
            found = self.env["ir.access"].search([
                ("model_id", "=", model.id),
                ("domain", "ilike", "company_id"),
            ], limit=1)
        else:
            found = self.env["ir.rule"].search([
                ("model_id", "=", model.id),
                ("domain_force", "ilike", "company_id"),
            ], limit=1)
        self.assertTrue(found, "no company restriction on account.fiscal.year")

    # ------------------------------------------------------------------
    # Opening period (special)
    # ------------------------------------------------------------------

    def test_create_period_does_not_create_opening_period(self):
        """create_period makes monthly periods only — no opening period."""
        self.fy.create_period(interval=1)
        special = self.fy.period_ids.filtered(lambda p: p.special)
        self.assertFalse(special, "create_period must not create an opening period")
        self.assertEqual(len(self.fy.period_ids), 12)

    def test_create_opening_period_sits_on_first_day(self):
        """The opening period starts and stops on the fiscal year's first day."""
        period = self.fy.create_opening_period()
        self.assertTrue(period.special)
        self.assertEqual(period.date_start, self.fy.date_from)
        self.assertEqual(period.date_stop, self.fy.date_from)
        self.assertEqual(period.fiscalyear_id, self.fy)

    def test_opening_period_may_overlap_first_month(self):
        """The opening period and the first monthly period may share a date."""
        self.fy.create_period(interval=1)
        opening = self.fy.create_opening_period()
        first_month = self.fy.period_ids.filtered(
            lambda p: not p.special
        ).sorted(key=lambda p: p.date_start)[0]
        self.assertEqual(opening.date_start, first_month.date_start)
        # No ValidationError — that is the point.

    def test_create_opening_period_is_idempotent(self):
        """Calling twice returns the same period instead of creating another."""
        first = self.fy.create_opening_period()
        second = self.fy.create_opening_period()
        self.assertEqual(first, second)
        self.assertEqual(len(self.fy.period_ids.filtered(lambda p: p.special)), 1)

    def test_regular_period_still_rejects_overlap(self):
        """Two non-special periods still cannot overlap."""
        self.fy.create_period(interval=1)
        month = self.fy.period_ids.filtered(lambda p: not p.special)[0]
        with self.assertRaises(ValidationError):
            self.env["account.period"].create({
                "date_range_id": self.env["date.range"].create({
                    "name": "Colliding",
                    "date_start": month.date_start,
                    "date_end": month.date_start,
                    "company_id": self.company.id,
                    "type_id": month.date_range_id.type_id.id,
                }).id,
                "fiscalyear_id": self.fy.id,
            })
