# Copyright 2026 Vertel Sverige AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)
"""T/11824 - stub dates land on the last day of the period by default.

Legacy (the OCA account_asset_management data the SFA database was migrated
from) booked every periodisation stub on the last day of the month. The
module's own default kept the start date's day-of-month, so two conventions
ended up in the same table. ``stub_month_end`` makes the convention a switch,
on by default.
"""

import datetime

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestDeferredStubDates(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.partner = cls.env["res.partner"].create({"name": "T11824 Partner"})
        cls.expense_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "expense"),
                ("company_ids", "in", cls.company.id),
            ],
            limit=1,
        )
        cls.period_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "asset_current"),
                ("company_ids", "in", cls.company.id),
            ],
            limit=1,
        )
        cls.profile = cls.env["account.deferred.profile"].create(
            {
                "name": "T11824 Profile",
                "rec_type": "deferred_expense",
                "account_depreciation_id": cls.period_account.id,
                "account_expense_id": cls.expense_account.id,
                "journal_id": cls.journal.id,
                "method_number": 3,
                "method_period": "month",
                "company_id": cls.company.id,
            }
        )

    def _periodise(self, date_start, periods=3, method_period="month",
                   stub_month_end=None):
        vals = {
            "name": "T11824 deferred",
            "profile_id": self.profile.id,
            "rec_type": "deferred_expense",
            "partner_id": self.partner.id,
            "company_id": self.company.id,
            "account_depreciation_id": self.period_account.id,
            "account_expense_id": self.expense_account.id,
            "journal_id": self.journal.id,
            "amount_total": 300.0,
            "date_start": date_start,
            "method_period": method_period,
            "method_number": periods,
        }
        if stub_month_end is not None:
            vals["stub_month_end"] = stub_month_end
        deferred = self.env["account.deferred"].create(vals)
        deferred._generate_stubs()
        return deferred

    # ── The default ────────────────────────────────────────────────────
    def test_01_company_default_is_month_end(self):
        """The company sets the convention to month-end out of the box."""
        self.assertTrue(self.company.deferred_stub_month_end)

    def test_02_profile_default_is_month_end(self):
        """A new profile inherits the month-end convention."""
        self.assertTrue(self.profile.stub_month_end)

    # ── Month-end dates ────────────────────────────────────────────────
    def test_03_month_end_clamps_to_short_months(self):
        """January start -> 31, 28/29, 31 - short months clamp, they do not
        overflow into the next month."""
        deferred = self._periodise("2026-01-15")
        dates = deferred.line_ids.sorted("sequence").mapped("date")
        self.assertEqual(
            dates,
            [
                datetime.date(2026, 1, 31),
                datetime.date(2026, 2, 28),
                datetime.date(2026, 3, 31),
            ],
        )

    def test_04_month_end_handles_leap_year(self):
        """February in a leap year ends on the 29th."""
        deferred = self._periodise("2024-01-10")
        dates = deferred.line_ids.sorted("sequence").mapped("date")
        self.assertEqual(
            dates,
            [
                datetime.date(2024, 1, 31),
                datetime.date(2024, 2, 29),
                datetime.date(2024, 3, 31),
            ],
        )

    def test_05_start_on_month_end_stays_on_month_end(self):
        """A start date already on the last day keeps landing on the last day."""
        deferred = self._periodise("2026-07-31")
        dates = deferred.line_ids.sorted("sequence").mapped("date")
        self.assertEqual(
            dates,
            [
                datetime.date(2026, 7, 31),
                datetime.date(2026, 8, 31),
                datetime.date(2026, 9, 30),
            ],
        )

    def test_06_quarterly_lands_on_quarter_end(self):
        """Quarterly periods land on the last day of each *quarter*.

        The last day is the first day of the next period minus one day, so a
        January start ends Q1 on 31 March - not on 31 January.
        """
        deferred = self._periodise(
            "2026-01-15", periods=4, method_period="quarter")
        dates = deferred.line_ids.sorted("sequence").mapped("date")
        self.assertEqual(
            dates,
            [
                datetime.date(2026, 3, 31),
                datetime.date(2026, 6, 30),
                datetime.date(2026, 9, 30),
                datetime.date(2026, 12, 31),
            ],
        )

    def test_07_yearly_lands_on_year_end(self):
        """Yearly periods land on 31 December, whatever the start month."""
        deferred = self._periodise("2026-06-15", periods=2, method_period="year")
        dates = deferred.line_ids.sorted("sequence").mapped("date")
        self.assertEqual(
            dates,
            [datetime.date(2026, 12, 31), datetime.date(2027, 12, 31)],
        )

    # ── The switch off ─────────────────────────────────────────────────
    def test_08_switch_off_keeps_start_day(self):
        """Turning the switch off restores date_start + N months."""
        deferred = self._periodise("2026-01-15", stub_month_end=False)
        dates = deferred.line_ids.sorted("sequence").mapped("date")
        self.assertEqual(
            dates,
            [
                datetime.date(2026, 1, 15),
                datetime.date(2026, 2, 15),
                datetime.date(2026, 3, 15),
            ],
        )

    def test_09_switch_off_on_profile(self):
        """The profile carries the switch, so the wizard's entries follow it."""
        profile = self.env["account.deferred.profile"].create({
            "name": "T11824 Profile start-day",
            "rec_type": "deferred_expense",
            "account_depreciation_id": self.period_account.id,
            "account_expense_id": self.expense_account.id,
            "journal_id": self.journal.id,
            "method_number": 3,
            "method_period": "month",
            "company_id": self.company.id,
            "stub_month_end": False,
        })
        vals = profile._get_deferred_vals()
        self.assertFalse(vals["stub_month_end"])
        vals.update({
            "name": "T11824 from profile",
            "company_id": self.company.id,
            "amount_total": 300.0,
            "date_start": "2026-01-15",
            "method_period": "month",
            "method_number": 3,
        })
        deferred = self.env["account.deferred"].create(vals)
        deferred._generate_stubs()
        self.assertEqual(
            deferred.line_ids.sorted("sequence").mapped("date"),
            [
                datetime.date(2026, 1, 15),
                datetime.date(2026, 2, 15),
                datetime.date(2026, 3, 15),
            ],
        )

    # ── Re-planning ────────────────────────────────────────────────────
    def test_10_toggling_switch_replans_unposted_stubs(self):
        """Saving the entry with the switch flipped re-plans the open stubs."""
        deferred = self._periodise("2026-01-15")
        deferred.write({"stub_month_end": False})
        self.assertEqual(
            deferred.line_ids.sorted("sequence").mapped("date"),
            [
                datetime.date(2026, 1, 15),
                datetime.date(2026, 2, 15),
                datetime.date(2026, 3, 15),
            ],
        )

    def test_11_posted_stubs_are_never_moved(self):
        """A posted stub keeps its date, and its period is not regenerated.

        Regression: ``_generate_stubs`` kept the posted stubs but restarted the
        schedule at period 1, so it produced a *second* stub for the period
        that was already booked (and a duplicate sequence).
        """
        deferred = self._periodise("2026-01-15")
        first = deferred.line_ids.sorted("sequence")[0]
        first.write({"posted": True})
        deferred.write({"stub_month_end": False})
        self.assertEqual(
            first.date,
            fields.Date.to_date("2026-01-31"),
            "a posted stub must never be re-dated",
        )
        unposted = deferred.line_ids.filtered(lambda line: not line.posted)
        self.assertEqual(
            unposted.sorted("sequence").mapped("date"),
            [datetime.date(2026, 2, 15), datetime.date(2026, 3, 15)],
        )

    def test_12_posted_stub_is_not_duplicated(self):
        """Re-planning never leaves two stubs for the same period."""
        deferred = self._periodise("2026-01-15")
        self.assertEqual(len(deferred.line_ids), 3)
        first = deferred.line_ids.sorted("sequence")[0]
        first.write({"posted": True})
        deferred.write({"stub_month_end": False})
        self.assertEqual(
            len(deferred.line_ids), 3,
            "re-planning created an extra stub for an already posted period",
        )
        sequences = deferred.line_ids.mapped("sequence")
        self.assertEqual(
            sequences, [10, 20, 30],
            f"duplicate or missing sequences after re-plan: {sequences}",
        )
