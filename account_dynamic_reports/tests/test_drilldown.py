# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestDrilldown(TransactionCase):
    """Every expression's drill-down must sum to the expression's value."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.country = cls.env.ref('base.se')
        # A tax group is mandatory on account.tax; create our own rather
        # than depend on a chart-specific xmlid, which differs per chart.
        cls.tax_group = cls.env['account.tax.group'].create({
            'name': 'Test Tax Group',
            'country_id': cls.country.id,
        })
        cls.company.country_id = cls.country
        # Odoo blocks posting a tax whose country differs from the
        # company's *fiscal* country; country_id alone is not enough.
        cls.company.account_fiscal_country_id = cls.country
        cls.journal = cls.env['account.journal'].search(
            [('type', '=', 'general'), ('company_id', '=', cls.company.id)], limit=1,
        )
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
            'name': 'Drilldown Test',
            'country_id': cls.country.id,
            'column_ids': [(0, 0, {'name': 'Balance', 'expression_label': 'balance'})],
        })
        cls.line_codes = cls.env['account.report.line'].create({
            'name': 'Codes',
            'code': 'DD_CODES',
            'report_id': cls.report.id,
            'sequence': 10,
            'expression_ids': [(0, 0, {
                'label': 'balance',
                'engine': 'account_codes',
                'formula': cls.account_a.code,
            })],
        })
        cls.line_domain = cls.env['account.report.line'].create({
            'name': 'Domain',
            'code': 'DD_DOMAIN',
            'report_id': cls.report.id,
            'sequence': 20,
            'expression_ids': [(0, 0, {
                'label': 'balance',
                'engine': 'domain',
                'subformula': 'sum',
                'formula': '[["account_id", "=", %d]]' % cls.account_a.id,
            })],
        })
        cls.line_tax = cls.env['account.report.line'].create({
            'name': 'Tax tags',
            'code': 'DD_TAX',
            'report_id': cls.report.id,
            'sequence': 30,
            'expression_ids': [(0, 0, {
                'label': 'balance',
                'engine': 'tax_tags',
                'formula': 'dd_10',
            })],
        })
        cls.line_sum = cls.env['account.report.line'].create({
            'name': 'Sum',
            'code': 'DD_SUM',
            'report_id': cls.report.id,
            'sequence': 40,
            'expression_ids': [(0, 0, {
                'label': 'balance',
                'engine': 'aggregation',
                'formula': 'DD_CODES.balance + DD_DOMAIN.balance',
            })],
        })

        cls.partner = cls.env['res.partner'].create({'name': 'DD Partner'})
        cls.tag = cls.env['account.account.tag']._get_tax_tags('dd_10', cls.country.id)
        cls.tag_pos = cls.tag.filtered(lambda t: not t.tax_negate)
        cls.tag_neg = cls.tag.filtered(lambda t: t.tax_negate)
        cls.tax = cls.env['account.tax'].create({
            'name': 'DD 10%', 'amount': 10.0, 'amount_type': 'percent',
            'type_tax_use': 'sale', 'company_id': cls.company.id,
            'country_id': cls.country.id,
            'tax_group_id': cls.tax_group.id,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {'repartition_type': 'tax',
                        'tag_ids': [(6, 0, cls.tag_pos.ids)]}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {'repartition_type': 'tax',
                        'tag_ids': [(6, 0, cls.tag_neg.ids)]}),
            ],
        })
        cls.sale_journal = cls.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', cls.company.id)], limit=1,
        )

    def _options(self):
        return {
            'date': {'date_from': '2026-01-01', 'date_to': '2026-12-31'},
            'company_ids': [self.company.id],
            'unfold_all': True,
        }

    def _setup_data(self):
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal.id,
            'date': '2026-05-01',
            'line_ids': [
                (0, 0, {'account_id': self.account_a.id, 'debit': 1000.0, 'name': 'a'}),
                (0, 0, {'account_id': self.account_b.id, 'credit': 1000.0, 'name': 'b'}),
            ],
        })
        move.action_post()

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.sale_journal.id,
            'invoice_date': '2026-05-02',
            'date': '2026-05-02',
            'invoice_line_ids': [(0, 0, {
                'name': 'svc', 'quantity': 1, 'price_unit': 500.0,
                'tax_ids': [(6, 0, self.tax.ids)],
            })],
        })
        invoice.action_post()

    def _value(self, line, options):
        # Pass every expression in the report: an aggregation resolves its
        # references among the expressions handed to it (as _get_lines does).
        totals = self.report._compute_expression_totals(
            self.report.line_ids.expression_ids, options,
        )
        return totals[(line.expression_ids.id, 'col_0')]

    def test_account_codes_drilldown_sums_to_value(self):
        self._setup_data()
        opts = self._options()
        value = self._value(self.line_codes, opts)
        lines = self.report._get_line_drilldown_lines(self.line_codes, opts)
        self.assertTrue(lines)
        self.assertAlmostEqual(sum(lines.mapped('balance')), value, 2)

    def test_domain_drilldown_sums_to_value(self):
        self._setup_data()
        opts = self._options()
        value = self._value(self.line_domain, opts)
        lines = self.report._get_line_drilldown_lines(self.line_domain, opts)
        self.assertTrue(lines)
        self.assertAlmostEqual(sum(lines.mapped('balance')), value, 2)

    def test_tax_tags_drilldown_sums_to_value(self):
        """The signed drill-down must equal the reported value exactly.

        A customer invoice sits on the credit side (balance = -50) while box
        10 reads +50, so the raw balance sum is -50. Only the signed amounts
        reproduce the figure -- which is the whole point of tooling.
        """
        self._setup_data()
        opts = self._options()
        value = self._value(self.line_tax, opts)
        self.assertAlmostEqual(value, 50.0, 2)  # 10% of 500

        lines = self.report._get_line_drilldown_lines(self.line_tax, opts)
        self.assertTrue(lines)
        self.assertAlmostEqual(sum(lines.mapped('balance')), -50.0, 2)

        signed = self.report._get_line_signed_amounts(self.line_tax, opts)
        self.assertAlmostEqual(sum(amount for _l, amount in signed), value, 2)

    def test_account_codes_negated_formula_drilldown(self):
        """A formula starting with '-' negates every line in the drill-down."""
        report = self.env['account.report'].create({
            'name': 'Negated',
            'column_ids': [(0, 0, {'name': 'B', 'expression_label': 'balance'})],
        })
        line = self.env['account.report.line'].create({
            'name': 'Neg', 'code': 'NEG', 'report_id': report.id, 'sequence': 10,
            'expression_ids': [(0, 0, {
                'label': 'balance', 'engine': 'account_codes',
                'formula': '-' + self.account_a.code,
            })],
        })
        self._setup_data()
        opts = self._options()
        totals = report._compute_expression_totals(line.expression_ids, opts)
        value = totals[(line.expression_ids.id, 'col_0')]
        self.assertAlmostEqual(value, -1000.0, 2)
        signed = report._get_line_signed_amounts(line, opts)
        self.assertAlmostEqual(sum(amount for _l, amount in signed), value, 2)

    def test_aggregation_drilldown_is_union(self):
        """An aggregation row drills down to the union of its references."""
        self._setup_data()
        opts = self._options()
        value = self._value(self.line_sum, opts)
        lines = self.report._get_line_drilldown_lines(self.line_sum, opts)
        self.assertTrue(lines)
        # DD_CODES and DD_DOMAIN both point at account_a, so the union is the
        # same set of lines -- and its sum is half the displayed value, because
        # the aggregation adds the two references.
        codes_lines = self.report._get_line_drilldown_lines(self.line_codes, opts)
        self.assertEqual(set(lines.ids), set(codes_lines.ids))
        self.assertAlmostEqual(sum(lines.mapped('balance')) * 2, value, 2)

    def test_aggregation_drilldown_unions_distinct_rows(self):
        report = self.env['account.report'].create({
            'name': 'Union Test',
            'column_ids': [(0, 0, {'name': 'B', 'expression_label': 'balance'})],
        })
        line_a = self.env['account.report.line'].create({
            'name': 'A', 'code': 'U_A', 'report_id': report.id, 'sequence': 10,
            'expression_ids': [(0, 0, {
                'label': 'balance', 'engine': 'account_codes',
                'formula': self.account_a.code,
            })],
        })
        line_b = self.env['account.report.line'].create({
            'name': 'B', 'code': 'U_B', 'report_id': report.id, 'sequence': 20,
            'expression_ids': [(0, 0, {
                'label': 'balance', 'engine': 'account_codes',
                'formula': self.account_b.code,
            })],
        })
        line_t = self.env['account.report.line'].create({
            'name': 'T', 'code': 'U_T', 'report_id': report.id, 'sequence': 30,
            'expression_ids': [(0, 0, {
                'label': 'balance', 'engine': 'aggregation',
                'formula': 'U_A.balance + U_B.balance',
            })],
        })
        self._setup_data()
        opts = self._options()
        union = report._get_line_drilldown_lines(line_t, opts)
        a_lines = report._get_line_drilldown_lines(line_a, opts)
        b_lines = report._get_line_drilldown_lines(line_b, opts)
        self.assertEqual(set(union.ids), set((a_lines | b_lines).ids))
        self.assertAlmostEqual(sum(union.mapped('balance')),
                               sum(a_lines.mapped('balance')) + sum(b_lines.mapped('balance')), 2)

    def test_drilldown_action_lists_the_lines(self):
        self._setup_data()
        opts = self._options()
        lines = self.report._get_line_drilldown_lines(self.line_codes, opts)
        action = self.line_codes._get_drilldown_action(lines)
        self.assertEqual(action['res_model'], 'account.move.line')
        self.assertEqual(action['domain'], [('id', 'in', lines.ids)])

    def test_unknown_engine_returns_empty(self):
        """A custom row without a handler yields no lines, not an error."""
        self.assertFalse(self.report._get_expression_lines(
            self.report.line_ids.filtered(lambda l: l.code == 'DD_TAX').expression_ids,
            self._options(),
        ) & self.env['account.move.line'].browse(-1))
