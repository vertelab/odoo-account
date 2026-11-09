# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Unit tests for the MIS expression converter.

These are pure-function tests: no database, no mis_builder install needed. The
inputs are strings taken from the actual Swedish data files, so a regression
here means a real KPI would convert wrongly.
"""

import json

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..models.mis_expression import (
    CONFIDENCE_EXACT,
    CONFIDENCE_REVIEW,
    CONFIDENCE_UNPARSED,
    ENGINE_ACCOUNT_CODES,
    ENGINE_AGGREGATION,
    ENGINE_DOMAIN,
    convert_expression,
)


@tagged('post_install', '-at_install')
class TestMisExpression(TransactionCase):

    # ------------------------------------------------------------------
    # bal[...] -> account_codes  (7.2)
    # ------------------------------------------------------------------
    def test_plain_balance(self):
        conv = convert_expression('bal[3000, 3001, 3002]')
        self.assertEqual(conv.engine, ENGINE_ACCOUNT_CODES)
        self.assertEqual(conv.formula, '3000,3001,3002')
        self.assertEqual(conv.confidence, CONFIDENCE_EXACT)

    def test_negated_suffix(self):
        """'* -1' must negate the whole sum, not just the first code."""
        conv = convert_expression('bal[3000, 3001, 3002]* -1')
        self.assertEqual(conv.engine, ENGINE_ACCOUNT_CODES)
        self.assertEqual(conv.formula, '-3000,3001,3002')
        self.assertTrue(conv.formula.startswith('-'))

    def test_negated_suffix_spaced(self):
        conv = convert_expression('bal[3000,3001] * -1')
        self.assertEqual(conv.formula, '-3000,3001')

    def test_range_token_survives(self):
        conv = convert_expression('bal[3500-3599]')
        self.assertEqual(conv.formula, '3500-3599')

    def test_initial_and_end_balance_get_from_beginning(self):
        for raw in ('bal_i[3000]', 'bal_e[3000]'):
            conv = convert_expression(raw)
            self.assertEqual(conv.engine, ENGINE_ACCOUNT_CODES, raw)
            self.assertEqual(conv.date_scope, 'from_beginning', raw)

    def test_variation_mode_is_strict_range(self):
        conv = convert_expression('balp[3000]')
        self.assertEqual(conv.engine, ENGINE_ACCOUNT_CODES)
        self.assertEqual(conv.date_scope, 'strict_range')

    # ------------------------------------------------------------------
    # crd[][domain] -> domain  (7.3)
    # ------------------------------------------------------------------
    def test_domain_is_json_not_account_codes(self):
        conv = convert_expression("crd[][('tax_line_id.name', '=', 'MP1')]")
        self.assertEqual(conv.engine, ENGINE_DOMAIN)
        parsed = json.loads(conv.formula)
        self.assertEqual(parsed, [['tax_line_id.name', '=', 'MP1']])
        self.assertEqual(conv.confidence, CONFIDENCE_REVIEW,
                         'crd ignores credit notes; flag it for review')

    def test_balance_with_domain_keeps_the_account_constraint(self):
        """`bal[2614][(tax...)]` means account 2614 AND that tax.

        Dropping the account selector sums every account carrying the tax,
        which is how box 30 became 3 750 instead of 1 875: the reverse-charge
        tax posts to both 2614 (output) and 2645 (input).
        """
        conv = convert_expression(
            "bal[2614][('tax_line_id.name','=','TFEU')]")
        self.assertEqual(conv.engine, ENGINE_DOMAIN)
        parsed = json.loads(conv.formula)
        self.assertEqual(parsed[0], '&',
                         'the account and tax clauses must be explicitly ANDed')
        self.assertIn(['account_id.code', '=like', '2614%'], parsed)
        self.assertIn(['tax_line_id.name', '=', 'TFEU'], parsed)

    def test_crd_over_account_codes_is_a_domain(self):
        """crd over codes sums credits only; account_codes would net it."""
        conv = convert_expression('crd[3106,3108]')
        self.assertEqual(conv.engine, ENGINE_DOMAIN)
        parsed = json.loads(conv.formula)
        self.assertIn(['credit', '!=', 0], parsed)
        # Odoo domain is prefix notation: the '|' tokens come first.
        self.assertEqual(parsed[0], '|')
        self.assertEqual(len([t for t in parsed if t == '|']), 1)

    # ------------------------------------------------------------------
    # balp[...] -> domain + strict_range  (7.4)
    # ------------------------------------------------------------------
    def test_balp_is_movement_not_partner_aggregation(self):
        """balp = bal + mode 'p' = movement in the period."""
        conv = convert_expression(
            "balp[][('tax_line_id.name','=','I')]")
        self.assertEqual(conv.engine, ENGINE_DOMAIN)
        self.assertEqual(conv.date_scope, 'strict_range')
        self.assertEqual(json.loads(conv.formula),
                         [['tax_line_id.name', '=', 'I']])

    # ------------------------------------------------------------------
    # sum / arithmetic -> aggregation  (7.5)
    # ------------------------------------------------------------------
    def test_sum_of_kpis(self):
        conv = convert_expression(
            'sum([KpiA, KpiB])', {'KpiA': 'CODE_A', 'KpiB': 'CODE_B'})
        self.assertEqual(conv.engine, ENGINE_AGGREGATION)
        self.assertEqual(conv.formula, 'CODE_A.balance + CODE_B.balance')

    def test_kpi_arithmetic(self):
        conv = convert_expression(
            'KpiA + KpiB - KpiC',
            {'KpiA': 'A', 'KpiB': 'B', 'KpiC': 'C'})
        self.assertEqual(conv.engine, ENGINE_AGGREGATION)
        self.assertEqual(conv.formula, 'A.balance + B.balance - C.balance')

    def test_unknown_kpi_in_sum_is_not_guessed(self):
        conv = convert_expression('sum([KpiA, Nope])', {'KpiA': 'A'})
        self.assertEqual(conv.confidence, CONFIDENCE_UNPARSED)
        self.assertIn('Nope', conv.note)

    # ------------------------------------------------------------------
    # Refusal path  (7.7)
    # ------------------------------------------------------------------
    def test_unknown_pattern_is_flagged_not_silently_zero(self):
        conv = convert_expression('some_unknown_function(1, 2)')
        self.assertEqual(conv.confidence, CONFIDENCE_UNPARSED)
        self.assertIn('UNCONVERTED', conv.note)
        self.assertIn('some_unknown_function', conv.note)
        # It still produces a usable expression (empty domain), never a crash.
        self.assertEqual(json.loads(conv.formula), [['id', '=', 0]])

    def test_empty_expression(self):
        conv = convert_expression('')
        self.assertEqual(conv.engine, ENGINE_AGGREGATION)
        self.assertEqual(conv.formula, '')

    def test_none_expression(self):
        conv = convert_expression(None)
        self.assertEqual(conv.engine, ENGINE_AGGREGATION)
