# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""End-to-end tests for the converter against a real mis.report."""

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestMisImport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = cls.env['account.report.mis.import']
        # Build a small MIS report by hand so the test does not depend on
        # l10n_se_mis being installed.
        cls.mis_report = cls.env['mis.report'].create({
            'name': 'Import Test Report',
        })
        cls.mis_report.kpi_ids = [
            (0, 0, {
                'name': 'LineA',
                'description': 'Line A',
                'sequence': 10,
                'expression_ids': [(0, 0, {'name': 'bal[3000,3001]'})],
            }),
            (0, 0, {
                'name': 'LineB',
                'description': 'Line B',
                'sequence': 20,
                'expression_ids': [
                    (0, 0, {'name': "crd[][('tax_line_id.name','=','MP1')]"})
                ],
            }),
            (0, 0, {
                'name': 'Heading',
                'description': 'A heading with no expression',
                'sequence': 30,
            }),
            (0, 0, {
                'name': 'Total',
                'description': 'Total',
                'sequence': 40,
                'expression_ids': [(0, 0, {'name': 'sum([LineA, LineB])'})],
            }),
        ]

    # ------------------------------------------------------------------
    # 7.8 idempotency and provenance
    # ------------------------------------------------------------------
    def test_conversion_creates_report_with_provenance(self):
        res = self.service.convert_report(self.mis_report)
        self.assertTrue(res['created'])
        report = self.env['account.report'].browse(res['report_id'])
        self.assertEqual(report.mis_report_id, self.mis_report)
        self.assertEqual(len(report.line_ids), 4)

    def test_second_run_creates_nothing(self):
        first = self.service.convert_report(self.mis_report)
        second = self.service.convert_report(self.mis_report)
        self.assertFalse(second['created'])
        self.assertEqual(second['report_id'], first['report_id'])
        self.assertEqual(
            self.env['account.report'].search_count(
                [('mis_report_id', '=', self.mis_report.id)]), 1)
        self.assertEqual(second['differences'], [])

    def test_second_run_reports_differences_instead_of_overwriting(self):
        first = self.service.convert_report(self.mis_report)
        report = self.env['account.report'].browse(first['report_id'])
        # Simulate a manual edit: drop a line.
        report.line_ids.filtered(lambda l: l.code == 'LINEA').unlink()
        second = self.service.convert_report(self.mis_report)
        self.assertFalse(second['created'])
        self.assertTrue(second['differences'],
                        'A removed line must be reported, not silently restored')
        self.assertIn('LINEA', ' '.join(second['differences']))

    # ------------------------------------------------------------------
    # 7.9 dry run
    # ------------------------------------------------------------------
    def test_dry_run_writes_nothing(self):
        before = self.env['account.report'].search_count([])
        res = self.service.convert_report(self.mis_report, dry_run=True)
        after = self.env['account.report'].search_count([])
        self.assertEqual(before, after, 'dry_run must not create reports')
        self.assertIsNone(res['report_id'])
        self.assertEqual(res['lines'], 4)

    def test_dry_run_counts_expressions(self):
        res = self.service.convert_report(self.mis_report, dry_run=True)
        # LineA 1 + LineB 1 + Total 1; the heading has none.
        self.assertEqual(res['expressions'], 3)

    # ------------------------------------------------------------------
    # 7.6 headings
    # ------------------------------------------------------------------
    def test_heading_becomes_line_without_expression(self):
        res = self.service.convert_report(self.mis_report)
        report = self.env['account.report'].browse(res['report_id'])
        heading = report.line_ids.filtered(lambda l: l.code == 'HEADING')
        self.assertTrue(heading)
        self.assertFalse(heading.expression_ids)

    # ------------------------------------------------------------------
    # 7.5 aggregation
    # ------------------------------------------------------------------
    def test_aggregation_references_generated_codes(self):
        res = self.service.convert_report(self.mis_report)
        report = self.env['account.report'].browse(res['report_id'])
        total = report.line_ids.filtered(lambda l: l.code == 'TOTAL')
        expr = total.expression_ids
        self.assertEqual(expr.engine, 'aggregation')
        self.assertIn('LINEA.balance', expr.formula)
        self.assertIn('LINEB.balance', expr.formula)

    # ------------------------------------------------------------------
    # Accounting data is never touched
    # ------------------------------------------------------------------
    def test_conversion_does_not_touch_accounting_data(self):
        move_count = self.env['account.move'].search_count([])
        line_count = self.env['account.move.line'].search_count([])
        self.service.convert_report(self.mis_report)
        self.assertEqual(self.env['account.move'].search_count([]), move_count)
        self.assertEqual(
            self.env['account.move.line'].search_count([]), line_count)
