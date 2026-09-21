# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestCurrencyRevaluationReport(TransactionCase):
    """Unrealized currency gains/losses on open receivables and payables."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company_currency = cls.company.currency_id
        cls.report = cls.env['account.report'].search(
            [('name', 'like', 'Unrealized Currency')], limit=1
        )
        cls.handler = cls.env['account.currency.revaluation.report.handler']

        # A foreign currency with a known rate, distinct from the company one.
        cls.foreign = cls.env['res.currency'].search(
            [('name', '=', 'USD'), ('active', 'in', (True, False))], limit=1
        )
        if not cls.foreign:
            cls.foreign = cls.env['res.currency'].create({
                'name': 'USD',
                'symbol': '$',
                'rate': 1.0,
            })
        cls.foreign.active = True
        # Odoo stores the rate as "1 company currency unit = <rate> foreign".
        # rate 0.5 therefore means 1 SEK = 0.5 USD, i.e. 1 USD = 2 SEK.
        cls.env['res.currency.rate'].create({
            'currency_id': cls.foreign.id,
            'name': '2026-01-01',
            'rate': 0.5,
            'company_id': cls.company.id,
        })

        cls.partner = cls.env['res.partner'].create({'name': 'FX Test Partner'})
        cls.receivable = cls.env['account.account'].search([
            ('account_type', '=', 'asset_receivable'),
            ('company_ids', 'in', cls.company.id),
        ], limit=1)
        cls.journal = cls.env['account.journal'].search(
            [('type', '=', 'general'), ('company_id', '=', cls.company.id)], limit=1
        )

    def _make_open_line(self, foreign_amount, company_amount, account=None,
                        partner=None, currency=None):
        """Create a posted entry with one open foreign-currency line."""
        account = account or self.receivable
        partner = partner or self.partner
        currency = currency or self.foreign
        move = self.env['account.move'].create({
            'journal_id': self.journal.id,
            'date': '2026-01-15',
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {
                    'account_id': account.id,
                    'partner_id': partner.id,
                    'currency_id': currency.id,
                    'debit': company_amount,
                    'credit': 0.0,
                    'amount_currency': foreign_amount,
                    'name': 'FX test line',
                }),
                (0, 0, {
                    'account_id': self.env['account.account'].search([
                        ('account_type', '=', 'equity_unaffected'),
                        ('company_ids', 'in', self.company.id),
                    ], limit=1).id,
                    'debit': 0.0,
                    'credit': company_amount,
                    'name': 'FX test counterline',
                }),
            ],
        })
        move.action_post()
        return move.line_ids.filtered(lambda l: l.account_id == account)

    def _options(self, date_to='2026-12-31'):
        return {
            'date': {'date_from': '2026-01-01', 'date_to': date_to},
            'company_ids': [self.company.id],
            'columns': {},
        }

    def _totals(self, date_to='2026-12-31'):
        return self.handler._get_revaluation_totals(self._options(date_to))

    def _adjustment(self, date_to='2026-12-31'):
        return self._totals(date_to)['adjustment']

    def _baseline(self, date_to='2026-12-31'):
        """Adjustment before the test adds its own entries.

        The test database may already contain foreign-currency entries, so
        assertions are made on the delta rather than absolute amounts.
        """
        return self._totals(date_to)

    # ------------------------------------------------------------------
    # Requirement: the report computes the unrealized difference
    # ------------------------------------------------------------------
    def test_adjustment_is_current_minus_operation(self):
        """Adjustment equals the foreign amount at the report rate minus booked."""
        base = self._baseline()
        # 1000 USD booked as 2000 SEK; rate 0.5 => 1 USD = 2 SEK => 2000 SEK.
        self._make_open_line(foreign_amount=1000.0, company_amount=2000.0)
        totals = self._totals()
        self.assertAlmostEqual(
            totals['balance_currency'] - base['balance_currency'], 1000.0, places=2)
        self.assertAlmostEqual(
            totals['balance_operation'] - base['balance_operation'], 2000.0, places=2)
        self.assertAlmostEqual(
            totals['balance_current'] - base['balance_current'], 2000.0, places=2)
        self.assertAlmostEqual(
            totals['adjustment'] - base['adjustment'], 0.0, places=2)

    def test_rate_change_produces_adjustment(self):
        """A rate differing from the booking rate yields a non-zero adjustment."""
        base = self._adjustment()
        # Book 1000 USD as 1000 SEK; at rate 0.5 (1 USD = 2 SEK) it is worth 2000.
        self._make_open_line(foreign_amount=1000.0, company_amount=1000.0)
        self.assertAlmostEqual(self._adjustment() - base, 1000.0, places=2)

    def test_fully_reconciled_line_is_excluded(self):
        """A settled foreign line must not affect the adjustment."""
        base = self._adjustment()
        line = self._make_open_line(foreign_amount=1000.0, company_amount=1000.0)
        self.assertAlmostEqual(self._adjustment() - base, 1000.0, places=2)

        # Fully reconcile it against a counter entry in the same currency.
        counter = self._make_open_line(foreign_amount=-1000.0, company_amount=-1000.0)
        (line + counter).reconcile()

        self.assertAlmostEqual(self._adjustment() - base, 0.0, places=2)

    def test_company_currency_lines_are_ignored(self):
        """Lines in the company currency are not revalued."""
        base = self._adjustment()
        self._make_open_line(
            foreign_amount=1000.0, company_amount=1000.0, currency=self.company_currency
        )
        self.assertAlmostEqual(self._adjustment() - base, 0.0, places=2)

    # ------------------------------------------------------------------
    # Requirement: the report is a decision aid, not a booking
    # ------------------------------------------------------------------
    def test_no_move_is_created(self):
        """Running the report must not create or change any entry."""
        self._make_open_line(foreign_amount=1000.0, company_amount=1000.0)
        moves_before = self.env['account.move'].search_count([])
        self.report._get_lines(self._options())
        self.assertEqual(self.env['account.move'].search_count([]), moves_before)

    # ------------------------------------------------------------------
    # Requirement: report renders and is reachable
    # ------------------------------------------------------------------
    def test_report_renders_both_lines(self):
        """The report renders its two sections with the four columns."""
        lines = self.report._get_lines(self._options())
        names = [l['name'] for l in lines]
        self.assertIn('Accounts To Adjust', names)
        self.assertIn('Excluded Accounts', names)
        for line in lines:
            self.assertEqual(len(line['columns']), 4)

    def test_excluded_line_is_zero_without_configuration(self):
        """Without configured exclusions the excluded section stays zero."""
        self._make_open_line(foreign_amount=1000.0, company_amount=1000.0)
        lines = self.report._get_lines(self._options())
        excluded = next(l for l in lines if l['name'] == 'Excluded Accounts')
        for col in excluded['columns']:
            self.assertAlmostEqual(col['no_format'], 0.0, places=2)

    def test_report_date_drives_the_rate(self):
        """The rate used is the one in effect at the report date."""
        self._make_open_line(foreign_amount=1000.0, company_amount=1000.0)
        # Record a rate change effective later in the year.
        self.env['res.currency.rate'].create({
            'currency_id': self.foreign.id,
            'name': '2026-07-01',
            'rate': 0.25,  # 1 SEK = 0.25 USD -> 1 USD = 4 SEK -> 1000 USD = 4000
            'company_id': self.company.id,
        })
        before = self.handler._get_revaluation_totals(self._options('2026-06-30'))
        after = self.handler._get_revaluation_totals(self._options('2026-12-31'))
        self.assertNotAlmostEqual(before['adjustment'], after['adjustment'], places=2)
