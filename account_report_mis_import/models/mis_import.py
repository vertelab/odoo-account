# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""The converter: mis.report -> account.report.

Design notes that matter when reading this
------------------------------------------
**Deduplicate on (report, name), not on xmlid.** Measured: 4 783
``mis.report.kpi`` records but only 4 685 unique xmlids -- the same KPI appears
in more than one data file. Keying on xmlid would create duplicate lines.

**Track provenance on the report.** ``mis_report_id`` makes the conversion
idempotent and lets a generated report be traced back. On a second run the
tool compares instead of overwriting, so a human edit to a generated report is
not silently destroyed.

**Never write accounting data.** The only models written are the four
``account.report*`` models. Checked by a test, not by good intentions.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .mis_expression import (
    CONFIDENCE_EXACT,
    CONFIDENCE_REVIEW,
    CONFIDENCE_UNPARSED,
    convert_expression,
)

_logger = logging.getLogger(__name__)


class AccountReportMisImport(models.Model):
    """Stateless service model; the work happens in the methods."""

    _name = 'account.report.mis.import'
    _description = 'MIS report to account.report converter'

    @api.model
    def convert_report(self, mis_report, dry_run=False, company=None):
        """Convert one ``mis.report`` into an ``account.report``.

        Returns a dict describing what happened::

            {'report_id': int|None, 'created': bool, 'lines': n,
             'expressions': n, 'warnings': [...], 'differences': [...],
             'dry_run': bool}
        """
        mis_report.ensure_one()
        company = company or self.env.company
        result = {
            'report_id': None,
            'created': False,
            'lines': 0,
            'expressions': 0,
            'warnings': [],
            'differences': [],
            'dry_run': dry_run,
        }

        # Existing conversion? Then compare, do not overwrite.
        existing = self.env['account.report'].search(
            [('mis_report_id', '=', mis_report.id)], limit=1)

        kpis = self._collect_kpis(mis_report)
        code_map = self._build_code_map(kpis)

        if dry_run:
            result['lines'] = len(kpis)
            result['expressions'] = sum(
                1 for kpi in kpis for _expr in kpi.expression_ids)
            result['report_id'] = existing.id or None
            result['created'] = not existing
            for kpi in kpis:
                for expr in kpi.expression_ids:
                    conv = convert_expression(expr.name, code_map)
                    if conv.confidence == CONFIDENCE_UNPARSED:
                        result['warnings'].append(
                            '%s / %s: %s' % (mis_report.name, kpi.name, conv.note))
            return result

        if existing:
            result['report_id'] = existing.id
            result['differences'] = self._diff_report(existing, kpis, code_map)
            return result

        report = self._create_report(mis_report, company, kpis, code_map, result)
        result['report_id'] = report.id
        result['created'] = True
        return result

    # ------------------------------------------------------------------
    # Reading the source
    # ------------------------------------------------------------------
    @api.model
    def _collect_kpis(self, mis_report):
        """The report's KPIs, de-duplicated on name.

        A KPI may appear in several data files; the last one wins, which is
        what Odoo itself does when loading them.
        """
        seen = {}
        for kpi in mis_report.kpi_ids.sorted(lambda k: (k.sequence, k.id)):
            seen[kpi.name] = kpi
        return list(seen.values())

    @api.model
    def _build_code_map(self, kpis):
        """MIS KPI name -> generated line code.

        Codes must be unique per report and stable across runs, so they are
        derived from the KPI name rather than from the id.
        """
        code_map = {}
        used = set()
        for kpi in kpis:
            base = self._sanitise_code(kpi.name)
            code = base
            suffix = 1
            while code in used:
                suffix += 1
                code = '%s_%d' % (base, suffix)
            used.add(code)
            code_map[kpi.name] = code
        return code_map

    @staticmethod
    def _sanitise_code(name):
        """A line code is a short uppercase token; keep it readable."""
        cleaned = ''.join(ch if (ch.isalnum() or ch == '_') else '_' for ch in name)
        return cleaned.upper()[:32] or 'KPI'

    # ------------------------------------------------------------------
    # Writing the target
    # ------------------------------------------------------------------
    @api.model
    def _create_report(self, mis_report, company, kpis, code_map, result):
        report = self.env['account.report'].create({
            'name': mis_report.name,
            'mis_report_id': mis_report.id,
            'country_id': company.account_fiscal_country_id.id or False,
            'column_ids': [(0, 0, {
                'name': _('Balance'),
                'expression_label': 'balance',
                'figure_type': 'monetary',
                'sequence': 1,
            })],
        })

        for kpi in kpis:
            self._create_line(report, kpi, code_map, result)
        return report

    @api.model
    def _create_line(self, report, kpi, code_map, result):
        line_vals = {
            'name': kpi.description or kpi.name,
            'code': code_map[kpi.name],
            'report_id': report.id,
            'sequence': kpi.sequence or 10,
        }
        expressions = kpi.expression_ids
        if not expressions:
            # An abstract heading: a line with no expression at all. This is
            # 2 139 of the 4 685 rows -- a converter that demands an expression
            # per row would lose half the structure.
            self.env['account.report.line'].create(line_vals)
            result['lines'] += 1
            return

        expr_commands = []
        for expr in expressions:
            conv = convert_expression(expr.name, code_map)
            vals = {
                'label': 'balance',
                'engine': conv.engine,
                'formula': conv.formula,
            }
            if conv.subformula:
                vals['subformula'] = conv.subformula
            elif conv.engine == 'domain':
                # A database CHECK requires every domain expression to carry a
                # subformula. The engine treats it as the aggregation mode
                # ('sum' vs 'count'); the converter always wants a sum.
                vals['subformula'] = 'sum'
            if conv.date_scope:
                vals['date_scope'] = conv.date_scope
            expr_commands.append((0, 0, vals))

            if conv.confidence == CONFIDENCE_UNPARSED:
                result['warnings'].append(
                    '%s / %s: %s' % (report.name, kpi.name, conv.note))
            elif conv.confidence == CONFIDENCE_REVIEW:
                result['warnings'].append(
                    'REVIEW %s / %s: %s' % (report.name, kpi.name, conv.note))

        line_vals['expression_ids'] = expr_commands
        self.env['account.report.line'].create(line_vals)
        result['lines'] += 1
        result['expressions'] += len(expr_commands)

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------
    @api.model
    def _diff_report(self, report, kpis, code_map):
        """Compare the existing report against a fresh conversion.

        Returns a list of human-readable differences. Deliberately does not
        write anything: a second run must never silently undo a manual fix.
        """
        differences = []
        existing_lines = {line.code: line for line in report.line_ids}
        for kpi in kpis:
            code = code_map.get(kpi.name)
            line = existing_lines.get(code)
            if not line:
                differences.append('missing line: %s (%s)' % (kpi.name, code))
                continue
            expected = len(kpi.expression_ids)
            actual = len(line.expression_ids)
            if expected != actual:
                differences.append(
                    'line %s: %d expressions in source, %d in report'
                    % (code, expected, actual))
        extra = set(existing_lines) - set(code_map.values())
        for code in sorted(extra):
            differences.append('extra line in report: %s' % code)
        return differences
