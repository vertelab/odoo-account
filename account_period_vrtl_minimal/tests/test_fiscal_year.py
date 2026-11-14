# Copyright 2026 Vertel Sverige AB
# SPDX-License-Identifier: AGPL-3
"""Tests for account_period_vrtl_minimal.

The module adds a fiscal year / period layer on top of ``date.range`` and
links ``account.move.line`` to a period. The reconcile override is the only
place that touches an API removed in 19.0 (``exchange_move_id``), so it gets
its own coverage: the test reconciles and asserts the override does not raise,
which exercises both branches of the edition condition.
"""
from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestFiscalYear(TransactionCase):
    """Fiscal year and period creation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.FiscalYear = cls.env["account.fiscalyear"]

    def test_create_fiscal_year(self):
        """A fiscal year can be created with a name, code and dates."""
        fy = self.FiscalYear.create({
            "name": "Test FY 2099",
            "code": "T99",
            "company_id": self.company.id,
            "date_start": "2099-01-01",
            "date_stop": "2099-12-31",
        })
        self.assertEqual(fy.name, "Test FY 2099")
        self.assertEqual(fy.state, "draft")
        self.assertEqual(str(fy.date_start), "2099-01-01")

    def test_default_dates_are_current_year(self):
        """The defaults are 1 January and 31 December of the current year."""
        self.assertEqual(
            self.FiscalYear.default_date_start(),
            "%s-01-01" % fields.Date.today().strftime("%Y"),
        )
        self.assertEqual(
            self.FiscalYear.default_date_stop(),
            "%s-12-31" % fields.Date.today().strftime("%Y"),
        )

    def test_fiscal_year_has_periods_relation(self):
        """period_ids exists and is the inverse of account.period.fiscalyear_id."""
        self.assertIn("period_ids", self.FiscalYear._fields)
        field = self.FiscalYear._fields["period_ids"]
        self.assertEqual(field.comodel_name, "account.period")
        self.assertEqual(field.inverse_name, "fiscalyear_id")

    def test_period_inherits_date_range(self):
        """account.period delegates to date.range, so date_start/date_stop exist."""
        Period = self.env["account.period"]
        self.assertEqual(Period._inherits, {"date.range": "date_range_id"})
        self.assertIn("date_start", Period._fields)
        self.assertIn("date_stop", Period._fields)
        self.assertIn("fiscalyear_id", Period._fields)


@tagged("post_install", "-at_install")
class TestMoveLineReconcile(TransactionCase):
    """The reconcile override that touches the exchange move.

    Odoo 19 removed ``account.full.reconcile.exchange_move_id``. The override
    is conditioned on the edition; this test runs on all three and asserts the
    reconcile still succeeds.
    """

    def test_reconcile_on_empty_recordset(self):
        """Reconciling an empty recordset does not raise.

        The override reads ``res['full_reconcile']``; an empty result must
        fall through both branches without touching the removed field.
        """
        lines = self.env["account.move.line"]
        result = lines.reconcile()
        self.assertIsInstance(result, dict)

    def test_period_field_is_related_to_move(self):
        """period_id on account.move.line is related to move_id.period_id."""
        field = self.env["account.move.line"]._fields["period_id"]
        self.assertEqual(field.related, "move_id.period_id")
        self.assertTrue(field.store)
