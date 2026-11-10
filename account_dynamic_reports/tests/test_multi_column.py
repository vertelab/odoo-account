# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestMultiColumnEngine(TransactionCase):
    """A report can show IB / period movement / UB as three columns."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.journal = cls.env['account.journal'].search(
            [('type', '=', 'general'), ('company_id', '=', cls.company.id)], limit=1,
        )
        # Two accounts inside the code range we report on.
        cls.account_a = cls.env['account.account'].search(
            [('company_ids', 'in', cls.company.id), ('account_type', '=', 'asset_current')],
            limit=1,
        )
        cls.account_b = cls.env['account.account'].search(
            [('company_ids', 'in', cls.company.id), ('account_type', '=', 'asset_current'),
             ('id', '!=', cls.account_a.id)],
            limit=1,
        )
        if not cls.account_a or not cls.account_b:
            raise cls.skipTest(cls, "Need two asset accounts in the chart")

        cls.report = cls.env['account.report'].create({
            'name': 'Multi Column Test',
            'column_ids': [
                (0, 0, {
                    'name': 'IB',
                    'expression_label': 'balance',
                    'date_from': False,
                    'date_to': fields.Date.to_date('2025-12-31'),
                    'date_scope': 'from_beginning',
                }),
                (0, 0, {
                    'name': 'Rorelse',
                    'expression_label': 'balance',
                    'date_from': fields.Date.to_date('2026-01-01'),
                    'date_to': fields.Date.to_date('2026-12-31'),
                    'date_scope': 'strict_range',
                }),
                (0, 0, {
                    'name': 'UB',
                    'expression_label': 'balance',
                    'date_from': False,
                    'date_to': fields.Date.to_date('2026-12-31'),
                    'date_scope': 'from_beginning',
                }),
            ],
        })
        cls.line_a = cls.env['account.report.line'].create({
            'name': 'Account A',
            'code': 'MC_A',
            'report_id': cls.report.id,
            'sequence': 10,
            'expression_ids': [(0, 0, {
                'label': 'balance',
                'engine': 'account_codes',
                'formula': cls.account_a.code,
            })],
        })
        cls.line_b = cls.env['account.report.line'].create({
            'name': 'Account B',
            'code': 'MC_B',
            'report_id': cls.report.id,
            'sequence': 20,
            'expression_ids': [(0, 0, {
                'label': 'balance',
                'engine': 'account_codes',
                'formula': cls.account_b.code,
            })],
        })
        cls.line_total = cls.env['account.report.line'].create({
            'name': 'Total',
            'code': 'MC_TOTAL',
            'report_id': cls.report.id,
            'sequence': 30,
            'expression_ids': [(0, 0, {
                'label': 'balance',
                'engine': 'aggregation',
                'formula': 'MC_A.balance + MC_B.balance',
            })],
        })

    def _move(self, date, lines):
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal.id,
            'date': date,
            'line_ids': [(0, 0, vals) for vals in lines],
        })
        move.action_post()
        return move

    def _balance_line(self, account, debit=0.0, credit=0.0):
        return {
            'account_id': account.id,
            'debit': debit,
            'credit': credit,
            'name': 'x',
        }

    def _options(self):
        return {
            'date': {'date_from': '2026-01-01', 'date_to': '2026-12-31'},
            'company_ids': [self.company.id],
            'unfold_all': True,
        }

    def test_three_columns_get_three_groups(self):
        groups = self.report._get_column_groups(self._options())
        self.assertEqual(len(groups), 3)
        self.assertEqual([g['key'] for g in groups], ['col_0', 'col_1', 'col_2'])
        self.assertEqual(groups[0]['date_scope'], 'from_beginning')
        self.assertEqual(groups[1]['date_scope'], 'strict_range')
        self.assertFalse(groups[0]['date_from'])
        self.assertEqual(groups[1]['date_from'], fields.Date.to_date('2026-01-01'))

    def test_single_column_report_gets_one_group(self):
        report = self.env['account.report'].create({'name': 'Plain'})
        groups = report._get_column_groups(self._options())
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['key'], 'col_0')
        self.assertEqual(groups[0]['date_from'], '2026-01-01')

    def test_ib_movement_ub_are_independent(self):
        """1000 booked in 2025, 500 booked in 2026.

        IB   (from_beginning, <= 2025-12-31) = 1000
        Move (strict_range, 2026)            =  500
        UB   (from_beginning, <= 2026-12-31) = 1500
        """
        self._move('2025-06-01', [
            self._balance_line(self.account_a, debit=1000.0),
            self._balance_line(self.account_b, credit=1000.0),
        ])
        self._move('2026-06-01', [
            self._balance_line(self.account_a, debit=500.0),
            self._balance_line(self.account_b, credit=500.0),
        ])

        totals = self.report._compute_expression_totals(
            self.line_a.expression_ids, self._options(),
        )
        expr_id = self.line_a.expression_ids.id
        self.assertAlmostEqual(totals[(expr_id, 'col_0')], 1000.0, 2)
        self.assertAlmostEqual(totals[(expr_id, 'col_1')], 500.0, 2)
        self.assertAlmostEqual(totals[(expr_id, 'col_2')], 1500.0, 2)

    def test_aggregation_sums_per_column(self):
        """The total line must sum each column separately, not mix periods."""
        self._move('2025-06-01', [
            self._balance_line(self.account_a, debit=1000.0),
            self._balance_line(self.account_b, credit=1000.0),
        ])
        self._move('2026-06-01', [
            self._balance_line(self.account_a, debit=500.0),
            self._balance_line(self.account_b, credit=500.0),
        ])

        totals = self.report._compute_expression_totals(
            self.report.line_ids.expression_ids, self._options(),
        )
        total_expr = self.line_total.expression_ids.id
        self.assertAlmostEqual(totals[(total_expr, 'col_0')], 0.0, 2)
        self.assertAlmostEqual(totals[(total_expr, 'col_1')], 0.0, 2)
        self.assertAlmostEqual(totals[(total_expr, 'col_2')], 0.0, 2)

    def test_lines_render_one_value_per_column(self):
        self._move('2025-06-01', [
            self._balance_line(self.account_a, debit=1000.0),
            self._balance_line(self.account_b, credit=1000.0),
        ])
        self._move('2026-06-01', [
            self._balance_line(self.account_a, debit=500.0),
            self._balance_line(self.account_b, credit=500.0),
        ])

        lines = self.report._get_lines(self._options())
        by_code = {line['name']: line for line in lines}
        self.assertIn('Account A', by_code)
        columns = by_code['Account A']['columns']
        self.assertEqual(len(columns), 3)
        self.assertAlmostEqual(columns[0]['no_format'], 1000.0, 2)
        self.assertAlmostEqual(columns[1]['no_format'], 500.0, 2)
        self.assertAlmostEqual(columns[2]['no_format'], 1500.0, 2)

    def test_aggregation_leading_minus_applies_to_every_term(self):
        """'-A-B' must negate BOTH terms, not just the first.

        A leading sign splits the formula into an empty first term, which
        offsets the operator list. Pairing operators and terms by index gave
        the second term the previous term's sign: '-A-B' became '-A+B'.
        On the K2 balance sheet that flipped equity and liabilities from
        +90 000 to -90 000.
        """
        report = self.env['account.report'].create({
            'name': 'Aggregation sign test',
            'column_ids': [(0, 0, {'name': 'B', 'expression_label': 'balance'})],
        })
        line_a = self.env['account.report.line'].create({
            'name': 'A', 'code': 'AGG_A', 'report_id': report.id, 'sequence': 10,
            'expression_ids': [(0, 0, {
                'label': 'balance', 'engine': 'account_codes',
                'formula': self.account_a.code})],
        })
        line_b = self.env['account.report.line'].create({
            'name': 'B', 'code': 'AGG_B', 'report_id': report.id, 'sequence': 20,
            'expression_ids': [(0, 0, {
                'label': 'balance', 'engine': 'account_codes',
                'formula': self.account_b.code})],
        })
        line_neg = self.env['account.report.line'].create({
            'name': 'Neg', 'code': 'AGG_NEG', 'report_id': report.id, 'sequence': 30,
            'expression_ids': [(0, 0, {
                'label': 'balance', 'engine': 'aggregation',
                'formula': '-AGG_A.balance-AGG_B.balance'})],
        })
        # A gets +1000, B gets -1000 (from the two sides of the entry).
        self._move('2026-05-01', [
            self._balance_line(self.account_a, debit=1000.0),
            self._balance_line(self.account_b, credit=1000.0),
        ])

        opts = self._options()
        totals = report._compute_expression_totals(
            report.line_ids.expression_ids, opts)
        a_val = totals[(line_a.expression_ids.id, 'col_0')]
        b_val = totals[(line_b.expression_ids.id, 'col_0')]
        neg_val = totals[(line_neg.expression_ids.id, 'col_0')]

        # -A-B must equal -(A + B), whichever signs A and B happen to have.
        self.assertAlmostEqual(neg_val, -(a_val + b_val), 2)
        # And explicitly: with A=1000 and B=-1000 the result is 0, not 2000.
        self.assertAlmostEqual(a_val, 1000.0, 2)
        self.assertAlmostEqual(b_val, -1000.0, 2)
        self.assertAlmostEqual(neg_val, 0.0, 2)
