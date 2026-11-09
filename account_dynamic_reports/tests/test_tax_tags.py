# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestTaxTagsEngine(TransactionCase):
    """The tax_tags engine: sum posted move lines carrying an account.tax tag."""

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

        cls.report = cls.env['account.report'].create({
            'name': 'Tax Tags Test Report',
            'country_id': cls.country.id,
            'column_ids': [(0, 0, {
                'name': 'Balance',
                'expression_label': 'balance',
            })],
        })
        cls.line_10 = cls.env['account.report.line'].create({
            'name': 'Box 10',
            'code': 'TT_10',
            'report_id': cls.report.id,
            'sequence': 10,
            'expression_ids': [(0, 0, {
                'label': 'balance',
                'engine': 'tax_tags',
                'formula': 'se_10',
            })],
        })
        cls.line_48 = cls.env['account.report.line'].create({
            'name': 'Box 48',
            'code': 'TT_48',
            'report_id': cls.report.id,
            'sequence': 15,
            'expression_ids': [(0, 0, {
                'label': 'balance',
                'engine': 'tax_tags',
                'formula': 'se_48',
            })],
        })
        tag48 = cls.env['account.account.tag']._get_tax_tags('se_48', cls.country.id)
        cls.tag48_pos = tag48.filtered(lambda t: not t.tax_negate)
        cls.tag48_neg = tag48.filtered(lambda t: t.tax_negate)

        # A label with no tag anywhere -- must render as 0, not crash.
        cls.line_missing = cls.env['account.report.line'].create({
            'name': 'Box missing',
            'code': 'TT_MISSING',
            'report_id': cls.report.id,
            'sequence': 20,
            'expression_ids': [(0, 0, {
                'label': 'balance',
                'engine': 'tax_tags',
                'formula': 'no_such_tag_xyz',
            })],
        })

        cls.journal = cls.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', cls.company.id)], limit=1,
        )
        cls.partner = cls.env['res.partner'].create({'name': 'VAT Test Partner'})

        # A 25 % sale tax whose tax repartition line carries '+se_10'.
        # The report line above already created both '+se_10' and '-se_10'
        # through account.report.expression.create(), so reuse them.
        tax_tag = cls.env['account.account.tag']._get_tax_tags('se_10', cls.country.id)
        cls.tag_pos = tax_tag.filtered(lambda t: not t.tax_negate)
        cls.tag_neg = tax_tag.filtered(lambda t: t.tax_negate)
        cls.tax = cls.env['account.tax'].create({
            'name': '25% Test Sale',
            'amount': 25.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'tax_group_id': cls.tax_group.id,
            'company_id': cls.company.id,
            'country_id': cls.country.id,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {
                    'repartition_type': 'tax',
                    'tag_ids': [(6, 0, cls.tag_pos.ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {
                    'repartition_type': 'tax',
                    'tag_ids': [(6, 0, cls.tag_neg.ids)],
                }),
            ],
        })

    def _options(self, date_from, date_to):
        return {
            'date': {'date_from': date_from, 'date_to': date_to},
            'company_ids': [self.company.id],
            'unfold_all': True,
        }

    def _invoice(self, amount, date, move_type='out_invoice', tax=None, journal=None):
        invoice = self.env['account.move'].create({
            'move_type': move_type,
            'partner_id': self.partner.id,
            'journal_id': (journal or self.journal).id,
            'invoice_date': date,
            'date': date,
            'invoice_line_ids': [(0, 0, {
                'name': 'Consulting',
                'quantity': 1,
                'price_unit': amount,
                'tax_ids': [(6, 0, (tax or self.tax).ids)],
            })],
        })
        invoice.action_post()
        return invoice

    def _value(self, line, options, warnings=None):
        totals = self.report._compute_expression_totals(
            line.expression_ids, options, warnings=warnings,
        )
        # Single-column report -> exactly one column group, key 'col_0'.
        return totals[(line.expression_ids.id, 'col_0')]

    def test_posted_invoice_is_summed(self):
        """A posted invoice tagged se_10 yields its tax amount."""
        self._invoice(1000.0, '2026-03-15')
        value = self._value(self.line_10, self._options('2026-01-01', '2026-12-31'))
        self.assertAlmostEqual(value, 250.0, 2)

    def test_draft_invoice_is_excluded(self):
        """Only posted entries count."""
        invoice = self._invoice(1000.0, '2026-03-15')
        invoice.button_draft()
        value = self._value(self.line_10, self._options('2026-01-01', '2026-12-31'))
        self.assertAlmostEqual(value, 0.0, 2)

    def test_date_scope_strict_range(self):
        """strict_range (the default) ignores entries outside the period."""
        self._invoice(1000.0, '2026-03-15')
        in_period = self._value(self.line_10, self._options('2026-01-01', '2026-12-31'))
        out_of_period = self._value(self.line_10, self._options('2026-04-01', '2026-12-31'))
        self.assertAlmostEqual(in_period, 250.0, 2)
        self.assertAlmostEqual(out_of_period, 0.0, 2)

    def test_credit_note_is_subtracted(self):
        """A credit note reduces the box: 250 output VAT - 100 credited."""
        self._invoice(1000.0, '2026-03-15')
        self._invoice(400.0, '2026-03-16', move_type='out_refund')
        value = self._value(self.line_10, self._options('2026-01-01', '2026-12-31'))
        self.assertAlmostEqual(value, 150.0, 2)  # 250 - 100

    def test_all_four_document_types(self):
        """The sign rule verified against every document type.

        Sale tax (box 10, tags +se_10 / -se_10):
            out_invoice  -250 balance, '+' tag -> +250
            out_refund   +100 balance, '-' tag -> -100
        Purchase tax (box 48, tags +se_48 / -se_48):
            in_invoice   +250 balance, '+' tag -> +250
            in_refund    -100 balance, '-' tag -> -100

        Box 10 must read 250 - 100 = 150; box 48 must read 250 - 100 = 150.
        """
        purchase_tax = self.env['account.tax'].create({
            'name': '25% Test Purchase',
            'amount': 25.0,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'tax_group_id': self.tax_group.id,
            'company_id': self.company.id,
            'country_id': self.country.id,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {'repartition_type': 'tax',
                        'tag_ids': [(6, 0, self.tag48_pos.ids)]}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {'repartition_type': 'tax',
                        'tag_ids': [(6, 0, self.tag48_neg.ids)]}),
            ],
        })
        purchase_journal = self.env['account.journal'].search(
            [('type', '=', 'purchase'), ('company_id', '=', self.company.id)], limit=1,
        )

        self._invoice(1000.0, '2026-03-15', move_type='out_invoice')
        self._invoice(400.0, '2026-03-16', move_type='out_refund')
        self._invoice(1000.0, '2026-03-17', move_type='in_invoice',
                      tax=purchase_tax, journal=purchase_journal)
        self._invoice(400.0, '2026-03-18', move_type='in_refund',
                      tax=purchase_tax, journal=purchase_journal)

        opts = self._options('2026-01-01', '2026-12-31')
        self.assertAlmostEqual(self._value(self.line_10, opts), 150.0, 2)
        self.assertAlmostEqual(self._value(self.line_48, opts), 150.0, 2)

    def test_missing_tag_renders_zero_and_warns(self):
        """A label whose tags have been removed gives 0.0 and one warning.

        The ORM auto-creates the +/- pair when the expression is created, so
        the tag must be removed for this case to occur -- which is exactly what
        happens when a data file is loaded without the country's chart, or when
        a tag is archived after a chart update.
        """
        self._invoice(1000.0, '2026-03-15')
        self.env['account.account.tag']._get_tax_tags(
            'no_such_tag_xyz', self.country.id,
        ).unlink()

        warnings = {}
        value = self._value(
            self.line_missing, self._options('2026-01-01', '2026-12-31'), warnings,
        )
        self.assertAlmostEqual(value, 0.0, 2)
        self.assertEqual(len(warnings), 1)
        key = next(iter(warnings))
        self.assertIn('no_such_tag_xyz', warnings[key]['message'])
        self.assertIn('Box missing', warnings[key]['message'])

    def test_report_without_country_warns_instead_of_crashing(self):
        """A report with no country cannot resolve tags; it must render 0."""
        report = self.env['account.report'].create({
            'name': 'No country report',
            'column_ids': [(0, 0, {'name': 'Balance', 'expression_label': 'balance'})],
        })
        line = self.env['account.report.line'].create({
            'name': 'Orphan line',
            'code': 'TT_NOC',
            'report_id': report.id,
            'sequence': 10,
            'expression_ids': [(0, 0, {
                'label': 'balance', 'engine': 'tax_tags', 'formula': 'se_10',
            })],
        })
        warnings = {}
        totals = report._compute_expression_totals(
            line.expression_ids, self._options('2026-01-01', '2026-12-31'),
            warnings=warnings,
        )
        self.assertAlmostEqual(totals[(line.expression_ids.id, 'col_0')], 0.0, 2)
        self.assertEqual(len(warnings), 1)

    def test_report_renders_with_tax_tags_engine(self):
        """The engine is wired into _get_lines, not only the helper."""
        self._invoice(1000.0, '2026-03-15')
        warnings = {}
        lines = self.report._get_lines(
            self._options('2026-01-01', '2026-12-31'), warnings=warnings,
        )
        by_code = {line['name']: line for line in lines}
        self.assertIn('Box 10', by_code)
        box10 = by_code['Box 10']
        self.assertAlmostEqual(box10['columns'][0]['no_format'], 250.0, 2)
        # The missing tag line still renders, as 0.
        self.assertIn('Box missing', by_code)
        self.assertAlmostEqual(by_code['Box missing']['columns'][0]['no_format'], 0.0, 2)
