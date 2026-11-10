# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
import re
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_round

_logger = logging.getLogger(__name__)

# Engine regexes
ACCOUNT_CODES_SPLIT_REGEX = re.compile(r'(?=[+-])')
ACCOUNT_CODES_TERM_REGEX = re.compile(
    r'^(?P<sign>[+-]?)'
    r'(?P<prefix>([A-Za-z\d.]+|tag\([\w.]+\))((?=\\)|(?<=[^CD])))'
    r'(\\\((?P<excluded_prefixes>([A-Za-z\d.]+,)*[A-Za-z\d.]*)\))?'
    r'(?P<balance_character>[DC]?)$'
)

class AccountReportLine(models.Model):
    _inherit = 'account.report.line'

    @api.model
    def _set_balance_sheet_date_scope(self):
        """Force date_scope=from_beginning on the balance sheet expressions.

        ``account_codes_formula`` creates the expressions for us but cannot
        set ``date_scope``, which defaults to ``strict_range``. Balance sheet
        accounts are cumulative: the opening balance of the fiscal year (and
        earlier) must be included, otherwise the report only shows movements
        inside the selected period and never balances.

        Called from data/balance_sheet.xml via <function>. Idempotent.
        """
        report = self.env.ref('account_dynamic_reports.balance_sheet',
                              raise_if_not_found=False)
        if not report:
            return True

    def _get_drilldown_action(self, move_lines):
        """An act_window listing the given move lines.

        Used by the drill-down route so the frontend can open the standard
        journal-items list instead of rendering its own table.
        """
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'account.action_account_moves_all'
        )
        action['domain'] = [('id', 'in', move_lines.ids)]
        action['context'] = {'create': False}
        action['display_name'] = self.name
        return action


class AccountReport(models.Model):
    _inherit = 'account.report'

    custom_handler_model_id = fields.Many2one(
        comodel_name='ir.model',
        string='Custom Handler',
        domain=[('model', 'like', 'account.report%handler')],
        help='Model implementing _custom_expression_eval(expr, options), used by '
             'expressions whose engine is "custom".',
    )

    @property
    def custom_handler_model_name(self):
        """Technical name of the custom handler model, if any."""
        self.ensure_one()
        return self.custom_handler_model_id.model if self.custom_handler_model_id else None

    # ========================================================================
    # REPORT GENERATION — Core engine
    # ========================================================================

    def _get_lines(self, options, all_column_groups_expression_totals=None, warnings=None):
        """Generate report lines for rendering.
        
        This is the main entry point called by the JS frontend.
        Returns a list of line dictionaries with columns, hierarchy, and values.
        """
        self.ensure_one()
        self.env.flush_all()

        # One balance map per report run. Without this the map would be
        # rebuilt for every expression and the whole point -- one query per
        # date window instead of one per expression -- would be lost.
        # Reset on entry so a later run never reuses an earlier run's data.
        self.env.cr._account_balance_cache = {}


        if warnings is not None:
            self._generate_common_warnings(options, warnings)

        # Compute expression totals for all expressions. The warnings dict is
        # handed down through the options so engine evaluators (tax_tags) can
        # report a missing label without crashing the report.
        if all_column_groups_expression_totals is None:
            all_column_groups_expression_totals = self._compute_expression_totals(
                self.line_ids.expression_ids, options, warnings=warnings
            )

        lines = []
        line_cache = {}
        hide_if_zero_lines = self.env['account.report.line']

        # Walk the line tree parent-first. A flat iteration over line_ids
        # (ordered by sequence, id) is not enough: a child may carry a lower
        # sequence than its parent, or a lower id when both share a sequence,
        # which would render the child before the parent it belongs to.
        for line in self._iter_lines_depth_first():
            parent_id = None
            if line.parent_id:
                if line.parent_id not in line_cache:
                    raise UserError(_(
                        "Line '%(child)s' is configured to appear before its parent '%(parent)s'. "
                        "The parent must always come first.",
                        child=line.name, parent=line.parent_id.name
                    ))
                parent_id = line_cache[line.parent_id]['id']

            line_dict = self._get_static_line_dict(
                options, line, all_column_groups_expression_totals, parent_id=parent_id
            )
            line_cache[line] = line_dict

            if line.hide_if_zero:
                hide_if_zero_lines |= line

            lines.append(line_dict)

        # Post-process: hide zero lines
        if hide_if_zero_lines:
            lines = self._hide_zero_lines(lines, hide_if_zero_lines)

        return lines

    def _iter_lines_depth_first(self):
        """Yield this report's lines parent-first, depth-first.

        Roots and siblings are ordered by (sequence, id); every parent is
        yielded before its children, so callers can rely on a parent already
        being present when a child is processed.
        """
        self.ensure_one()
        all_lines = self.line_ids

        def walk(line):
            yield line
            children = all_lines.filtered(lambda l: l.parent_id == line)
            for child in children.sorted(lambda l: (l.sequence, l.id)):
                yield from walk(child)

        roots = all_lines.filtered(lambda l: not l.parent_id)
        for root in roots.sorted(lambda l: (l.sequence, l.id)):
            yield from walk(root)

    def _get_columns(self, options):
        """Build the column descriptors the frontend renders.

        Each descriptor carries the ``column_group_key`` the engine used, so
        ``_get_static_line_dict()`` can pick the right value out of the
        per-group totals.
        """
        columns = []
        date_from = options.get('date', {}).get('date_from')
        date_to = options.get('date', {}).get('date_to')
        period_label = self._get_period_label(date_from, date_to)

        for group in self._get_column_groups(options):
            column = group['column']
            if column is None:
                # No explicit columns: one default column, as before.
                columns.append({
                    'name': period_label,
                    'expression_label': 'balance',
                    'figure_type': 'monetary',
                    'sortable': False,
                    'blank_if_zero': False,
                    'no_format': 0.0,
                    'column_group_key': group['key'],
                    'class': 'text-right',
                })
                continue

            columns.append({
                'name': column.name,
                'expression_label': column.expression_label,
                'figure_type': column.figure_type,
                'sortable': column.sortable,
                'blank_if_zero': column.blank_if_zero,
                'no_format': 0.0,
                'column_group_key': group['key'],
                'class': f'text-right o_figure_type_{column.figure_type}',
            })

        return columns

    def _get_period_label(self, date_from, date_to):
        """Generate a human-readable period label."""
        if date_from and date_to:
            return f"{date_from} → {date_to}"
        return _("Balance")

    def _get_static_line_dict(self, options, line, all_expression_totals, parent_id=None):
        """Create a line dictionary for a given report line."""
        columns = []
        line_id = f'report_line_{line.id}'

        for col in self._get_columns(options):
            expr_label = col.get('expression_label', 'balance')
            col_vals = {
                # A line without an expression (a heading) must print as an
                # empty cell, not as the column caption repeated on every row.
                'name': '',
                'expression_label': expr_label,
                'figure_type': col.get('figure_type', 'monetary'),
                'no_format': 0.0,
                'class': col.get('class', ''),
            }

            # Find matching expression. A line may carry several expressions
            # with the same label (one per column group in older data), so sum
            # the ones that belong to this column group.
            expr = line.expression_ids.filtered(lambda e: e.label == expr_label)
            if expr:
                group_key = col.get('column_group_key')
                total = sum(
                    all_expression_totals.get((e.id, group_key), 0.0) for e in expr
                )
                col_vals['no_format'] = total
                col_vals['name'] = self._format_value(total, col.get('figure_type', 'monetary'))

            columns.append(col_vals)

        return {
            'id': line_id,
            'code': line.code,
            'name': line.name,
            'unfoldable': bool(line.children_ids),
            'unfolded': not line.foldable,
            'columns': columns,
            'level': line.hierarchy_level or 1,
            'parent_id': parent_id,
            'class': '' if parent_id else 'o_account_reports_level0',
        }

    def _format_value(self, value, figure_type='monetary'):
        """Format a value for display."""
        if figure_type == 'monetary':
            currency = self.env.company.currency_id
            return currency.format(value) if currency else f"{value:,.2f}"
        elif figure_type == 'percentage':
            return f"{value:.1f}%"
        return str(value)

    def _hide_zero_lines(self, lines, hide_if_zero_lines):
        """Remove lines where all columns are zero."""
        line_ids_to_hide = set()
        for line_dict in lines:
            line_id = line_dict['id']
            model, res_id = self._get_model_info_from_id(line_id)
            if model == 'account.report.line' and res_id in hide_if_zero_lines.ids:
                if all(float_is_zero(c.get('no_format', 0), precision_digits=2) for c in line_dict['columns']):
                    line_ids_to_hide.add(line_id)
                    # Also hide children
                    child_ids = [l['id'] for l in lines if l.get('parent_id') == line_id]
                    line_ids_to_hide.update(child_ids)

        return [l for l in lines if l['id'] not in line_ids_to_hide]

    def _get_model_info_from_id(self, line_id):
        """Parse line id string like 'report_line_42' into model + res_id."""
        if line_id and line_id.startswith('report_line_'):
            return 'account.report.line', int(line_id[12:])
        return None, None

    # ========================================================================
    # EXPRESSION COMPUTATION
    # ========================================================================

    def _get_column_groups(self, options):
        """Resolve the report's columns into column groups, each with its own
        date interval and date scope.

        A *column group* is what the engine computes values for. Today one
        column equals one group, but keeping the indirection means comparison
        columns (period vs period) can be added later without touching the
        engines or the aggregation resolver.

        Returns a list of dicts in column order::

            {'key': 'col_<n>', 'date_from': ..., 'date_to': ...,
             'date_scope': ..., 'column': <account.report.column> or None}

        A report without explicit columns gets exactly one group carrying the
        report-level dates from ``options``, so single-column reports behave
        exactly as before.
        """
        columns = self.column_ids
        if not columns:
            return [{
                'key': 'col_0',
                'date_from': options.get('date', {}).get('date_from'),
                'date_to': options.get('date', {}).get('date_to'),
                'date_scope': None,
                'column': None,
            }]

        groups = []
        report_from = options.get('date', {}).get('date_from')
        report_to = options.get('date', {}).get('date_to')
        for index, column in enumerate(columns):
            scope = column.date_scope or 'strict_range'
            groups.append({
                'key': 'col_%s' % index,
                # A column without its own dates inherits the report period.
                # "From the beginning" has no lower bound by definition, so it
                # inherits nothing there -- the value would be misleading.
                'date_from': None if scope == 'from_beginning'
                             else (column.date_from or report_from),
                'date_to': column.date_to or report_to,
                'date_scope': scope,
                'column': column,
            })
        return groups

    def _compute_expression_totals(self, expressions, options, warnings=None):
        """Compute totals for all expressions, per column group.

        Aggregations reference other expressions by line code
        ('BS_TOTAL_CURRENT.balance + ...'), and a referenced line may be
        created after the referring one, so iterating expression_ids in id
        order is not enough: the referenced value would still be missing.

        Evaluate every non-aggregation expression first, then resolve the
        aggregations in dependency order -- separately for every column group,
        so a three-column balance sheet gets three independent sets of values.

        Returns a dict: {(expr_id, column_group_key): value}
        """
        totals = {}
        company_id = options.get('company_ids', [self.env.company.id])[0]
        column_groups = self._get_column_groups(options)

        # The balance map is read with raw SQL, so pending writes must reach
        # the database first. The ORM path used to see them anyway; SQL does
        # not. Without this flush a report run inside an open transaction
        # (tests, scripted comparisons) shows zeros for freshly created moves.
        self.env.flush_all()

        # Every call gets its own map. Without this a direct call (tests, the
        # comparison tool) would reuse whatever a previous report left behind
        # -- and a movement column would read the balance-sheet map.
        self.env.cr._account_balance_cache = {}

        for group in column_groups:
            date_from = group['date_from']
            date_to = group['date_to']
            group_scope = group['date_scope']
            group_key = group['key']

            aggregations = self.env['account.report.expression']
            for expr in expressions:
                expr_key = (expr.id, group_key)
                # A column-level date scope wins over the expression's own,
                # so one expression can serve several columns (IB / movement /
                # UB) without being duplicated per column.
                scope_override = group_scope
                if expr.engine == 'account_codes':
                    totals[expr_key] = self._eval_account_codes(
                        expr, date_from, date_to, company_id, date_scope=scope_override,
                    )
                elif expr.engine == 'domain':
                    totals[expr_key] = self._eval_domain(expr, date_from, date_to, company_id)
                elif expr.engine == 'tax_tags':
                    totals[expr_key] = self._eval_tax_tags(
                        expr, date_from, date_to, company_id,
                        warnings=warnings, date_scope=scope_override,
                    )
                elif expr.engine == 'custom':
                    totals[expr_key] = self._eval_custom(expr, options)
                elif expr.engine == 'aggregation':
                    aggregations |= expr
                else:
                    totals[expr_key] = 0.0

            # Resolve aggregations. Loop until every one is computed; each pass
            # evaluates the expressions whose dependencies are already known.
            pending = aggregations
            while pending:
                progressed = False
                still_pending = self.env['account.report.expression']
                for expr in pending:
                    deps = self._aggregation_dependencies(expr, expressions)
                    if all((dep.id, group_key) in totals for dep in deps):
                        totals[(expr.id, group_key)] = self._eval_aggregation(
                            expr, totals, expressions, column_group_key=group_key,
                        )
                        progressed = True
                    else:
                        still_pending |= expr
                if not progressed:
                    # Circular or dangling reference: evaluate what is left with
                    # the values known so far so the report still renders.
                    for expr in still_pending:
                        totals[(expr.id, group_key)] = self._eval_aggregation(
                            expr, totals, expressions, column_group_key=group_key,
                        )
                    break
                pending = still_pending

        return totals

    def _aggregation_dependencies(self, expr, expressions):
        """Expressions referenced by an aggregation formula.

        Formulas look like 'CODE.label + CODE.label'; resolve each CODE to the
        matching expression so the caller can order the evaluation.
        """
        formula = (expr.formula or '').replace(' ', '')
        if not formula or formula == 'sum_children':
            return self.env['account.report.expression']
        deps = self.env['account.report.expression']
        for term in re.split(r'[+\-]', formula):
            if '.' not in term:
                continue
            line_code, expr_label = term.split('.', 1)
            deps |= expressions.filtered(
                lambda e: e.report_line_id.code == line_code and e.label == expr_label
            )
        return deps

    def _date_scope_domain(self, date_from, date_to, company_id, scope):
        """Build the date conditions for a period scope.

        Shared by every engine and by the drill-down, so a value and the
        transactions behind it can never disagree about which entries they
        cover.
        """
        scope = scope or 'strict_range'
        domain = []
        if scope == 'from_beginning':
            if date_to:
                domain.append(('date', '<=', date_to))
        elif scope == 'from_fiscalyear':
            domain.append(('date', '>=', self._get_fiscalyear_start(date_to, company_id)))
            if date_to:
                domain.append(('date', '<=', date_to))
        else:
            if date_from:
                domain.append(('date', '>=', date_from))
            if date_to:
                domain.append(('date', '<=', date_to))
        return domain

    def _get_balance_map(self, date_from, date_to, company_id, scope):
        """{account_code: balance} for one date window, fetched in ONE query.

        Why this exists
        ---------------
        A balance sheet has ~80 ``account_codes`` expressions, each with its
        own account list. Evaluating them one by one meant one SQL search per
        expression -- measured at 73 searches x 41.6 ms = 3 037 ms on a
        customer database.

        Fetching every line and summing in Python was *worse* (85 247 ORM
        objects, 3 443 ms). Letting the database group by account takes 61 ms.

        The map is cached per (date_from, date_to, scope, company_id) for the
        duration of one report run. The key must include the resolved window,
        not just the scope name: ``from_fiscalyear`` depends on ``date_to``,
        and ``from_beginning`` has no lower bound while ``strict_range`` does.
        Collapsing those into one key would turn a movement report into a
        balance report.
        """
        # The cache hangs off the cursor. It must be the SAME dict object for
        # every expression in one report run, and neither env.context nor an
        # attribute on env survives: each recordset gets a fresh Environment.
        # The cursor is the one object shared by the whole run.
        cache = getattr(self.env.cr, '_account_balance_cache', None)
        if cache is None:
            cache = {}
            self.env.cr._account_balance_cache = cache
        key = (date_from, date_to, scope or 'strict_range', company_id)
        if key in cache:
            return cache[key]

        domain = [('company_id', '=', company_id),
                  ('parent_state', '=', 'posted')]
        domain += self._date_scope_domain(date_from, date_to, company_id, scope)

        # Build the query explicitly instead of digging through the ORM's
        # query object: the shape we need (join + group by account) is simple,
        # and it stays readable.
        #
        # Odoo 18 stores the account code in a jsonb column named
        # 'code_store' (the field has no plain 'code' column, and Field in
        # 18.0 exposes no column_name attribute). Verified against
        # account_account.code_store in the database.
        code_field = 'code_store'
        conditions = ["aml.company_id = %s", "aml.parent_state = 'posted'"]
        params = [company_id]
        for field, operator, value in domain:
            if field == 'date' and operator in ('>=', '<='):
                conditions.append("aml.date %s %%s" % operator)
                params.append(value)
        where = " AND ".join(conditions)
        try:
            self.env.cr.execute(f"""
                SELECT aa.{code_field}->>'1' AS code, SUM(aml.balance) AS balance
                  FROM account_move_line aml
                  JOIN account_account aa ON aa.id = aml.account_id
                 WHERE {where}
                 GROUP BY aa.{code_field}
            """, params)
            rows = self.env.cr.fetchall()
        except Exception as exc:
            # A shared map feeds every line at once. Silently returning {} would
            # render a report full of 0,00 that looks like real amounts -- far
            # worse than a visible failure. Raise instead.
            _logger.exception(
                "Balance map failed (report %s, window %s..%s, scope %s)",
                self.name, date_from, date_to, scope)
            raise UserError(_(
                "Kunde inte hämta kontosaldon för rapporten '%(report)s' "
                "(%(from)s..%(to)s): %(error)s",
                report=self.name, **{'from': date_from or '-', 'to': date_to or '-'},
                error=exc,
            )) from exc

        balances = {}
        for code, balance in rows:
            if code:
                balances[code] = balances.get(code, 0.0) + (balance or 0.0)

        cache[key] = balances
        return balances

    def _sum_from_balance_map(self, expr, balances):
        """Sum the accounts in ``balances`` that match the expression's formula.

        Uses the same prefix semantics as ``_account_codes_to_domain`` --
        comma lists, ranges (``3500-3599``), percent suffixes (``48%``) and a
        leading ``-`` -- but matches against account codes in memory instead
        of building a domain.
        """
        if not expr.formula:
            return 0.0
        account_domain = self._account_codes_to_domain(expr.formula)
        if not account_domain:
            return 0.0

        leaves = self._flatten_account_domain(account_domain)
        if leaves is None:
            # The domain uses something we cannot evaluate in memory
            # (tag() or an odd shape): fall back to the SQL path rather than
            # returning a wrong number.
            return None

        includes, excludes = leaves
        total = 0.0
        for code, balance in balances.items():
            if any(code.startswith(p) for p in includes) and not any(
                    code.startswith(p) for p in excludes):
                total += balance
        return total

    def _flatten_account_domain(self, domain):
        """Reduce an account-code domain to (include_prefixes, exclude_prefixes).

        Returns None when the domain contains a condition we cannot express as
        a prefix (e.g. ``tag(...)``), so the caller can fall back to SQL.
        """
        includes, excludes = [], []
        negate_next = False
        for token in domain:
            if token == '!':
                negate_next = True
                continue
            if isinstance(token, str):
                # '&' and '|' carry no information for a flat prefix list.
                continue
            if not isinstance(token, (list, tuple)) or len(token) != 3:
                return None
            field, operator, value = token
            if field != 'account_id.code' or operator not in ('=like', 'not like'):
                return None
            if not isinstance(value, str) or not value.endswith('%'):
                return None
            prefix = value[:-1]
            if operator == 'not like':
                excludes.append(prefix)
            elif negate_next:
                excludes.append(prefix)
            else:
                includes.append(prefix)
            negate_next = False
        if not includes:
            return None
        return includes, excludes

    def _eval_account_codes(self, expr, date_from, date_to, company_id, date_scope=None):
        """Evaluate an account_codes expression like '1,2' or '+40-49'.

        ``date_scope`` decides which entries are summed:

            from_beginning  all entries up to the report end date (balance
                            sheet accounts — the opening balance is included)
            strict_range    only entries inside the report period (P&L)
            from_fiscalyear entries from the start of the fiscal year

        Anything else falls back to the report period.

        ``date_scope`` overrides the expression's own scope; the engine passes
        the column's scope so one expression can serve an opening-balance
        column and a period-movement column at once.
        """
        if not expr.formula:
            return 0.0

        # Fast path: sum from the shared balance map (one query per date
        # window instead of one per expression). Falls back to the SQL path
        # when the formula contains something a prefix cannot express.
        balances = self._get_balance_map(
            date_from, date_to, company_id, date_scope or expr.date_scope,
        )
        balance = self._sum_from_balance_map(expr, balances)
        if balance is None:
            lines = self._get_account_codes_lines(
                expr, date_from, date_to, company_id, date_scope=date_scope,
            )
            balance = sum(line.balance for line in lines)
        # A formula whose first term is negative ('-3-4-5-6-7-8') expresses
        # the negated sum of those accounts. Subtract the positive part
        # instead of adding it.
        if expr.formula.lstrip().startswith('-'):
            balance = -balance
        return float_round(balance, precision_digits=2)

    def _eval_tax_tags(self, expr, date_from, date_to, company_id, warnings=None,
                       date_scope=None):
        """Evaluate a tax_tags expression such as ``se_10``.

        The formula names an ``account.account.tag`` label (without the
        leading ``+``/``-``). Every posted line whose ``tax_tag_ids`` contains
        any tag of that name inside the report period is summed.

        Unlike ``account_codes`` the sign is not taken from the formula. It is
        taken from the tag itself, via ``account.account.tag.tax_negate``
        ("Negate Tax Balance"):

        * the tag **name** decides which box the line feeds — ``+se_10`` feeds
          box 10, ``-se_10`` the negative counterpart; both flavours are looked
          up and summed into the same expression;
        * the tag **polarity** decides the sign of the amount:
          ``contribution = -abs(balance)`` when ``tax_negate`` is set,
          ``+abs(balance)`` otherwise.

        Using the absolute value is what makes the four document types come out
        right, verified against a Swedish chart (see ``tests/test_tax_tags.py``):

        ==============  =======  ========  ========
        document        balance  tag       counted
        ==============  =======  ========  ========
        out_invoice     -250     +          +250
        out_refund      +100     -          -100
        in_invoice      +250     +          +250
        in_refund       -100     -          -100
        ==============  =======  ========  ========

        Note that a sale and a purchase never share a tag name in practice:
        output VAT goes to ``+se_10`` and input VAT to ``+se_48``, so the two
        +250 above land in *different* boxes. The sign flip for credit notes
        comes entirely from the invoice/refund tag pairing (the refund side of
        a repartition line carries the ``-`` tag), so the engine needs to know
        nothing about document types.

        ``date_scope`` is honoured the same way as for ``account_codes``:
        VAT boxes use ``strict_range`` (the default), balance-sheet style
        reports may use ``from_beginning``.

        A label that matches no tag yields 0.0 and a warning; the report still
        renders (see D6 in the change design).
        """
        if not expr.formula:
            return 0.0

        tag_name = expr.formula.strip()
        if not tag_name:
            return 0.0

        country_id = expr.report_line_id.report_id.country_id.id
        if not country_id:
            # Without a country the tag lookup cannot match anything, and
            # _get_tax_tags_domain() would crash on a False name. Treat it as
            # a missing tag rather than an error.
            self._warn_missing_tax_tag(expr, tag_name, country_id, warnings)
            return 0.0
        tags = self.env['account.account.tag']._get_tax_tags(tag_name, country_id)
        if not tags:
            self._warn_missing_tax_tag(expr, tag_name, country_id, warnings)
            return 0.0

        domain = [('company_id', '=', company_id),
                  ('parent_state', '=', 'posted'),
                  ('tax_tag_ids', 'in', tags.ids)]
        domain += self._date_scope_domain(
            date_from, date_to, company_id,
            date_scope or expr.date_scope or 'strict_range',
        )

        lines = self.env['account.move.line'].search(domain)
        total = 0.0
        for line in lines:
            # A line may carry several tags (e.g. '+se_30' and '+se_48' on the
            # same repartition line). Each tag contributes with its own
            # polarity, so a line matching both a '+' and a '-' tag of the same
            # name nets out -- which is the correct reading of tax_negate.
            for tag in line.tax_tag_ids & tags:
                total += -abs(line.balance) if tag.tax_negate else abs(line.balance)
        return float_round(total, precision_digits=2)

    def _warn_missing_tax_tag(self, expr, tag_name, country_id, warnings=None):
        """Report a tax_tags label that has no matching account.account.tag.

        This is not an error: ``account.report.expression.create()``
        auto-creates the ``+label``/``-label`` pair for the report's country,
        so a missing tag means the data file was loaded without a country (or
        the label is a typo). Either way the box must still render as 0 rather
        than crash the whole report.
        """
        line = expr.report_line_id
        report = line.report_id
        message = _(
            "Tax tag '%(tag)s' is missing for line '%(line)s' (code %(code)s) "
            "in report '%(report)s'; the value is shown as 0.",
            tag=tag_name, line=line.name, code=line.code or '-', report=report.name,
        )
        _logger.warning(message)
        if warnings is not None:
            warnings['account_dynamic_reports.missing_tax_tag_%s_%s' % (
                report.id, expr.id,
            )] = {'alert_type': 'warning', 'message': message}
        return 0.0

    def _get_fiscalyear_start(self, date_to, company_id):
        """First day of the fiscal year containing ``date_to``."""
        date_to = fields.Date.to_date(date_to) if date_to else fields.Date.today()
        company = self.env['res.company'].browse(company_id)
        fy = company.compute_fiscalyear_dates(date_to)
        return fy['date_from']

    def _account_codes_to_domain(self, formula):
        """Convert an account codes expression to an Odoo domain.

        The formula is a comma-separated list of terms. Each term is an
        optional sign (+/-), an account-code prefix, an optional exclusion
        list in parentheses, and an optional balance character (D/C):

            '1,2'               → accounts starting with 1 or 2 (OR)
            '+40-49'            → accounts 40xx minus 49xx
            '4\\\\(4010,4020)'   → class 4 excluding 4010 and 4020
            '3,4,5,6,7,8'       → classes 3 through 8 (OR)

        Returns None when nothing could be parsed, so callers can decide
        whether to fall back to a zero result.
        """
        account_codes = []
        exclude_codes = []

        terms = ACCOUNT_CODES_SPLIT_REGEX.split(formula)
        if not terms or terms[0] == '':
            terms = terms[1:] if len(terms) > 1 else [formula]

        # When the formula starts with '-', the minus signs separate terms of
        # a negated sum ('-3-4-5-6-7-8' = -(3 + 4 + ... + 8)) rather than
        # meaning "everything except". Treat those terms as inclusions; the
        # caller negates the total.
        leading_minus = formula.lstrip().startswith('-')

        for term in terms:
            match = ACCOUNT_CODES_TERM_REGEX.match(term)
            if not match:
                # Tolerate a bare comma-separated prefix list ('16,17'):
                # the term regex only accepts a single prefix, so expand it
                # here instead of silently dropping the whole expression.
                sign = term[0] if term[0] in '+-' else '+'
                body = (term[1:] if term[0] in '+-' else term).strip()
                prefixes = [p for p in body.split(',') if p]
                if prefixes and all(
                    re.fullmatch(r'[A-Za-z\d.]+', p) for p in prefixes
                ):
                    for prefix in prefixes:
                        entry = ('account_id.code', '=like', f"{prefix}%")
                        # A formula starting with '-' negates the whole sum
                        # ('-3000,3001,3002' = -(3000+3001+3002)). Every term
                        # is then an inclusion; the caller flips the total.
                        effective_sign = '+' if leading_minus else sign
                        (account_codes if effective_sign == '+'
                         else exclude_codes).append(entry)
                continue

            sign = match.group('sign') or '+'
            if leading_minus:
                # '-3-4-5-6-7-8': every term is an inclusion.
                sign = '+'
            prefix = match.group('prefix')
            excluded = match.group('excluded_prefixes') or ''
            # The trailing D/C ('1510D' = debit balance only) is parsed by the
            # regex but not applied: filtering on the sign of the balance is a
            # per-line condition that a domain cannot express. No Swedish data
            # uses it (measured: zero occurrences), so it is documented here
            # rather than silently ignored. If it ever appears, the row must
            # become a 'domain' expression with ('balance', '>', 0).
            if match.group('balance_character'):
                _logger.warning(
                    "account_codes: balance character %r in %r is not applied; "
                    "convert the row to a domain expression instead.",
                    match.group('balance_character'), formula,
                )

            # Handle tag() references
            if prefix.startswith('tag('):
                tag_ref = prefix[4:-1]
                tag = self.env.ref(tag_ref, raise_if_not_found=False)
                if tag:
                    if sign == '+':
                        account_codes.append(('account_id.tag_ids', 'in', [tag.id]))
                    else:
                        exclude_codes.append(('account_id.tag_ids', 'in', [tag.id]))
                continue

            # Standard prefix matching
            prefix_like = f"{prefix}%"
            if excluded:
                excluded_list = excluded.split(',')
                if sign == '+':
                    account_codes.append(['&', ('account_id.code', '=like', prefix_like)] +
                        [('account_id.code', 'not like', f"{exc}%") for exc in excluded_list])
                else:
                    exclude_codes.append(['&', ('account_id.code', '=like', prefix_like)] +
                        [('account_id.code', 'not like', f"{exc}%") for exc in excluded_list])
            else:
                if sign == '+':
                    account_codes.append(('account_id.code', '=like', prefix_like))
                else:
                    exclude_codes.append(('account_id.code', '=like', prefix_like))

        # Build OR domain for includes, minus excludes
        if not account_codes:
            return None

        if len(account_codes) == 1:
            domain = account_codes[0]
        else:
            domain = ['|'] * (len(account_codes) - 1) + account_codes

        if exclude_codes:
            # Add exclusions as NOT conditions
            for excl in exclude_codes:
                domain = ['&', domain, '!', excl]

        return domain if isinstance(domain, list) else [domain]

    def _get_account_codes_lines(self, expr, date_from, date_to, company_id,
                                 date_scope=None):
        """The account.move.line recordset behind an account_codes expression.

        Returns an empty recordset when the formula cannot be parsed, so a
        value of 0 and an empty drill-down always agree.
        """
        if not expr.formula:
            return self.env['account.move.line']
        account_domain = self._account_codes_to_domain(expr.formula)
        if not account_domain:
            return self.env['account.move.line']
        domain = [('company_id', '=', company_id),
                  ('parent_state', '=', 'posted')]
        domain += self._date_scope_domain(
            date_from, date_to, company_id,
            date_scope or expr.date_scope or 'strict_range',
        )
        domain += account_domain
        return self.env['account.move.line'].search(domain)

    def _get_domain_lines(self, expr, date_from, date_to, company_id):
        """The account.move.line recordset behind a domain expression."""
        if not expr.formula:
            return self.env['account.move.line']
        try:
            domain = json.loads(expr.formula)
        except (json.JSONDecodeError, TypeError):
            return self.env['account.move.line']
        domain = list(domain)
        if company_id:
            domain = [('company_id', '=', company_id),
                      ('parent_state', '=', 'posted')] + domain
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        return self.env['account.move.line'].search(domain)

    def _get_tax_tags_lines(self, expr, date_from, date_to, company_id,
                            date_scope=None):
        """The account.move.line recordset behind a tax_tags expression.

        A line is included once for every tag of the wanted name it carries;
        the recordset is de-duplicated by the ORM, so the caller sees each
        transaction once even when it carries several matching tags.
        """
        tag_name = (expr.formula or '').strip()
        country_id = expr.report_line_id.report_id.country_id.id
        if not tag_name or not country_id:
            return self.env['account.move.line']
        tags = self.env['account.account.tag']._get_tax_tags(tag_name, country_id)
        if not tags:
            return self.env['account.move.line']
        domain = [('company_id', '=', company_id),
                  ('parent_state', '=', 'posted'),
                  ('tax_tag_ids', 'in', tags.ids)]
        domain += self._date_scope_domain(
            date_from, date_to, company_id,
            date_scope or expr.date_scope or 'strict_range',
        )
        return self.env['account.move.line'].search(domain)

    def _get_expression_lines(self, expr, options):
        """The account.move.line recordset a single expression sums.

        This is the drill-down: for every engine it returns exactly the lines
        the value was computed from, so the figures are auditable.

        Aggregations are handled by ``_get_line_drilldown_lines()`` because
        they own no lines of their own.
        """
        date_from = options.get('date', {}).get('date_from')
        date_to = options.get('date', {}).get('date_to')
        company_id = options.get('company_ids', [self.env.company.id])[0]
        group_key = options.get('column_group_key')
        date_scope = options.get('column_date_scope')

        if expr.engine == 'account_codes':
            return self._get_account_codes_lines(
                expr, date_from, date_to, company_id, date_scope=date_scope,
            )
        if expr.engine == 'domain':
            return self._get_domain_lines(expr, date_from, date_to, company_id)
        if expr.engine == 'tax_tags':
            return self._get_tax_tags_lines(
                expr, date_from, date_to, company_id, date_scope=date_scope,
            )
        if expr.engine == 'custom':
            handler_name = self.custom_handler_model_name
            if not handler_name:
                return self.env['account.move.line']
            handler = self.env[handler_name]
            method = getattr(handler, '_custom_expression_lines', None)
            if method is None:
                _logger.warning(
                    "Custom handler %s has no _custom_expression_lines (report %s)",
                    handler_name, self.name,
                )
                return self.env['account.move.line']
            return method(expr, options)
        # aggregation / external / anything else: no lines of its own.
        _ = group_key  # kept for readability at the call sites
        return self.env['account.move.line']

    def _get_expression_signed_amounts(self, expr, options):
        """Per-line signed contribution, as the engine counted it.

        A plain recordset cannot carry the sign: for ``tax_tags`` a customer
        invoice sits on the credit side (``balance`` = -250) while box 10 must
        read +250, because the sign comes from the tag (``tax_negate``) and not
        from the ledger. Returning ``(line, amount)`` pairs makes the
        drill-down add up to the displayed value for every engine.

        Returns a list of ``(line, amount)`` tuples.
        """
        lines = self._get_expression_lines(expr, options)
        if not lines:
            return []

        if expr.engine == 'tax_tags':
            tag_name = (expr.formula or '').strip()
            country_id = expr.report_line_id.report_id.country_id.id
            tags = self.env['account.account.tag']._get_tax_tags(tag_name, country_id)
            if not tags:
                return [(line, 0.0) for line in lines]
            result = []
            for line in lines:
                amount = 0.0
                for tag in line.tax_tag_ids & tags:
                    amount += (-abs(line.balance) if tag.tax_negate
                               else abs(line.balance))
                result.append((line, amount))
            return result

        if expr.engine == 'account_codes' and (expr.formula or '').lstrip().startswith('-'):
            # A negated sum ('-3-4-5-6') counts every line with the opposite
            # sign, so the drill-down must show that too.
            return [(line, -line.balance) for line in lines]

        if expr.engine == 'custom':
            # A custom handler defines its own sign convention. It may expose
            # ``_custom_expression_signed_amounts(expr, options, lines)``; when
            # it does, that is authoritative. Without it we fall back to the
            # raw balance, which is correct for handlers that simply sum.
            handler_name = self.custom_handler_model_name
            if handler_name:
                handler = self.env[handler_name]
                method = getattr(handler, '_custom_expression_signed_amounts', None)
                if method is not None:
                    amounts = method(expr, options, lines)
                    return list(zip(lines, amounts))
            return [(line, line.balance) for line in lines]

        return [(line, line.balance) for line in lines]

    def _get_line_signed_amounts(self, line, options):
        """Per-line signed contributions behind a whole report line."""
        self.ensure_one()
        result = []
        wanted = options.get('expression_label')
        for expr in line.expression_ids:
            if wanted and expr.label != wanted:
                continue
            if expr.engine == 'aggregation':
                for target in self._aggregation_drilldown_expressions(expr):
                    result.extend(self._get_expression_signed_amounts(target, options))
            else:
                result.extend(self._get_expression_signed_amounts(expr, options))
        return result

    def _get_line_drilldown_lines(self, line, options):
        """The recordset behind a whole report line.

        An aggregation row has no transactions of its own: its drill-down is
        the union of the rows it aggregates. That keeps the promise that the
        drill-down always sums to the displayed value.
        """
        self.ensure_one()
        result = self.env['account.move.line']
        for expr in line.expression_ids:
            if expr.label != options.get('expression_label', expr.label):
                continue
            if expr.engine == 'aggregation':
                result |= self._get_aggregation_drilldown_lines(expr, options)
            else:
                result |= self._get_expression_lines(expr, options)
        return result

    def _aggregation_drilldown_expressions(self, expr):
        """The expressions an aggregation formula references, recursively."""
        formula = (expr.formula or '').replace(' ', '')
        if not formula or formula == 'sum_children':
            return self.env['account.report.expression']
        all_expressions = expr.report_line_id.report_id.line_ids.expression_ids
        result = self.env['account.report.expression']
        for term in re.split(r'[+\-]', formula):
            if '.' not in term:
                continue
            line_code, expr_label = term.split('.', 1)
            targets = all_expressions.filtered(
                lambda e: e.report_line_id.code == line_code and e.label == expr_label
            )
            for target in targets:
                if target.engine == 'aggregation':
                    result |= self._aggregation_drilldown_expressions(target)
                else:
                    result |= target
        return result

    def _get_aggregation_drilldown_lines(self, expr, options):
        """Union of the referenced rows' transactions, per aggregation formula."""
        formula = (expr.formula or '').replace(' ', '')
        if not formula or formula == 'sum_children':
            return self.env['account.move.line']
        all_expressions = expr.report_line_id.report_id.line_ids.expression_ids
        result = self.env['account.move.line']
        for term in re.split(r'[+\-]', formula):
            if '.' not in term:
                continue
            line_code, expr_label = term.split('.', 1)
            targets = all_expressions.filtered(
                lambda e: e.report_line_id.code == line_code and e.label == expr_label
            )
            for target in targets:
                if target.engine == 'aggregation':
                    result |= self._get_aggregation_drilldown_lines(target, options)
                else:
                    result |= self._get_expression_lines(target, options)
        return result

    def _eval_aggregation(self, expr, totals, all_expressions, column_group_key=None):
        """Evaluate an aggregation expression like 'line_A.balance + line_B.balance'.

        Values are looked up for ``column_group_key``, so a three-column report
        sums each column independently instead of mixing periods.
        """
        formula = expr.formula or ''
        if formula == 'sum_children':
            return 0.0  # Handled by parent accumulation in JS

        # Parse formula: 'code1.label1 + code2.label2'
        #
        # A leading sign ('-A-B') splits into an EMPTY first term, so the
        # operator list and the term list are offset by one. Pairing them by
        # index then gives every term the previous term's sign -- '-A-B'
        # became '-A+B'. Walk the formula instead and carry the sign forward.
        total = 0.0
        compact = re.sub(r'\s+', '', formula)
        # Split on the sign, keeping the sign with the term that follows it.
        parts = re.findall(r'([+\-]?)([^+\-]+)', compact)

        for sign, term in parts:
            if not term or '.' not in term:
                continue
            op = sign or '+'

            # Find the expression by line code + label
            line_code, expr_label = term.split('.', 1)
            target_expr = all_expressions.filtered(
                lambda e: e.report_line_id.code == line_code and e.label == expr_label
            )
            if target_expr:
                val = totals.get((target_expr.id, column_group_key), 0.0)
                if op == '+':
                    total += val
                else:
                    total -= val

        return total

    def _eval_domain(self, expr, date_from, date_to, company_id):
        """Evaluate a domain expression."""
        if not expr.formula:
            return 0.0
        try:
            domain = json.loads(expr.formula)
        except (json.JSONDecodeError, TypeError):
            domain = [('id', '=', 0)]  # No results

        if company_id:
            domain = [('company_id', '=', company_id),
                      ('parent_state', '=', 'posted')] + domain
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))

        lines = self.env['account.move.line'].search(domain)
        subformula = expr.subformula or 'sum'
        if subformula == 'sum':
            return sum(line.balance for line in lines)
        elif subformula == 'neg_sum':
            # MIS Builder's `crd` returns credit - debit, while `balance` is
            # debit - credit. A migrated VAT box needs the MIS sign, or every
            # output-VAT box comes out negative.
            return -sum(line.balance for line in lines)
        elif subformula == 'count':
            return len(lines)
        return 0.0

    def _eval_custom(self, expr, options):
        """Evaluate a custom (Python) expression.

        The expression's ``formula`` names the method to call on the report's
        custom handler; ``subformula`` is passed through so one method can
        serve several columns. Defaults to ``_custom_expression_eval`` when no
        formula is set.
        """
        if not self.custom_handler_model_id:
            return 0.0
        handler_model = self.env[self.custom_handler_model_name]
        method_name = expr.formula or '_custom_expression_eval'
        if not hasattr(handler_model, method_name):
            _logger.warning(
                "Custom handler %s has no method %s (report %s)",
                self.custom_handler_model_name, method_name, self.name,
            )
            return 0.0
        return getattr(handler_model, method_name)(expr, options)
    def _generate_common_warnings(self, options, warnings):
        """Generate warnings for the report (e.g., unposted entries)."""
        date_to = options.get('date', {}).get('date_to', fields.Date.today())
        unposted = self.env['account.move'].search_count([
            ('date', '<=', date_to),
            ('state', '=', 'draft'),
            ('company_id', 'in', options.get('company_ids', [self.env.company.id])),
        ])
        if unposted:
            warnings['account_reports.unposted_entries'] = {
                'alert_type': 'warning',
                'message': _("There are %d unposted journal entries up to %s.", unposted, date_to),
            }

    # ========================================================================
    # CLIENT ACTION
    # ========================================================================

    # ------------------------------------------------------------------
    # PDF rendering (15.1/15.2)
    # ------------------------------------------------------------------
    def _dynamic_report_options(self):
        """The options the PDF is generated with.

        A printed report has no interactive date picker, so default to the
        current fiscal year to date. Kept in one method so the PDF and the
        frontend cannot drift apart.
        """
        self.ensure_one()
        today = fields.Date.context_today(self.env.user)
        fiscal = self.env.company.compute_fiscalyear_dates(today)
        return {
            'date': {
                'date_from': fields.Date.to_string(fiscal['date_from']),
                'date_to': fields.Date.to_string(today),
            },
            'company_ids': [self.env.company.id],
            'unfold_all': True,
        }

    def _dynamic_report_period_label(self):
        """Human readable period for the PDF header."""
        self.ensure_one()
        opts = self._dynamic_report_options()['date']
        if opts.get('date_from') and opts.get('date_to'):
            return '%s - %s' % (opts['date_from'], opts['date_to'])
        return ''

    def _dynamic_report_columns(self):
        self.ensure_one()
        return self._get_columns(self._dynamic_report_options())

    def _dynamic_report_pdf_lines(self):
        """Lines for the PDF, already hidden-zero-filtered and formatted.

        Uses the same ``_get_lines`` the frontend uses, so a printed report can
        never disagree with the screen.
        """
        self.ensure_one()
        return self._get_lines(self._dynamic_report_options())

    def open_report(self, options=None):
        """Open the report in the dynamic reports client action."""
        self.ensure_one()
        action = {
            'type': 'ir.actions.client',
            'tag': 'account_dynamic_report',
            'name': self.name,
            'context': {
                'report_id': self.id,
                'default_options': options or {},
            },
        }
        return action

    def action_open_dynamic_report(self):
        """Button action to open this report in the dynamic view."""
        return self.open_report()

