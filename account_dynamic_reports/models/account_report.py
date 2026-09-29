# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel AB
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

        if warnings is not None:
            self._generate_common_warnings(options, warnings)

        # Compute expression totals for all expressions
        if all_column_groups_expression_totals is None:
            all_column_groups_expression_totals = self._compute_expression_totals(
                self.line_ids.expression_ids, options
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
        """Get columns for the report based on options (date range, comparison, etc.)."""
        columns = []
        column_options = options.get('columns', {})
        
        # Date column (always first for grouped reports)
        date_from = options.get('date', {}).get('date_from')
        date_to = options.get('date', {}).get('date_to')
        period_label = self._get_period_label(date_from, date_to)

        for col in self.column_ids:
            columns.append({
                'name': col.name,
                'expression_label': col.expression_label,
                'figure_type': col.figure_type,
                'sortable': col.sortable,
                'blank_if_zero': col.blank_if_zero,
                'no_format': 0.0,
                'class': f'text-right o_figure_type_{col.figure_type}',
            })

        # If no custom columns defined, provide default
        if not columns:
            columns.append({
                'name': period_label,
                'expression_label': 'balance',
                'figure_type': 'monetary',
                'sortable': False,
                'blank_if_zero': False,
                'class': 'text-right',
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
                'name': col['name'],
                'expression_label': expr_label,
                'figure_type': col.get('figure_type', 'monetary'),
                'no_format': 0.0,
                'class': col.get('class', ''),
            }

            # Find matching expression
            expr = line.expression_ids.filtered(lambda e: e.label == expr_label)
            if expr:
                expr_key = (expr.id, None)
                total = all_expression_totals.get(expr_key, 0.0)
                col_vals['no_format'] = total
                col_vals['name'] = self._format_value(total, col.get('figure_type', 'monetary'))

            columns.append(col_vals)

        return {
            'id': line_id,
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

    def _compute_expression_totals(self, expressions, options):
        """Compute totals for all expressions given the current options.

        Aggregations reference other expressions by line code
        ('BS_TOTAL_CURRENT.balance + ...'), and a referenced line may be
        created after the referring one, so iterating expression_ids in id
        order is not enough: the referenced value would still be missing.

        Evaluate every non-aggregation expression first, then resolve the
        aggregations in dependency order.

        Returns a dict: {(expr_id, None): value}
        """
        totals = {}
        date_from = options.get('date', {}).get('date_from')
        date_to = options.get('date', {}).get('date_to')
        company_id = options.get('company_ids', [self.env.company.id])[0]

        aggregations = self.env['account.report.expression']
        for expr in expressions:
            expr_key = (expr.id, None)
            if expr.engine == 'account_codes':
                totals[expr_key] = self._eval_account_codes(expr, date_from, date_to, company_id)
            elif expr.engine == 'domain':
                totals[expr_key] = self._eval_domain(expr, date_from, date_to, company_id)
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
                if all((dep.id, None) in totals for dep in deps):
                    totals[(expr.id, None)] = self._eval_aggregation(expr, totals, expressions)
                    progressed = True
                else:
                    still_pending |= expr
            if not progressed:
                # Circular or dangling reference: evaluate what is left with
                # the values known so far so the report still renders.
                for expr in still_pending:
                    totals[(expr.id, None)] = self._eval_aggregation(expr, totals, expressions)
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

    def _eval_account_codes(self, expr, date_from, date_to, company_id):
        """Evaluate an account_codes expression like '1,2' or '+40-49'.

        ``date_scope`` decides which entries are summed:

            from_beginning  all entries up to the report end date (balance
                            sheet accounts — the opening balance is included)
            strict_range    only entries inside the report period (P&L)
            from_fiscalyear entries from the start of the fiscal year

        Anything else falls back to the report period.
        """
        if not expr.formula:
            return 0.0

        domain = [('company_id', '=', company_id),
                  ('parent_state', '=', 'posted')]

        scope = expr.date_scope or 'strict_range'
        if scope == 'from_beginning':
            if date_to:
                domain.append(('date', '<=', date_to))
        elif scope == 'from_fiscalyear':
            fiscal_start = self._get_fiscalyear_start(date_to, company_id)
            domain.append(('date', '>=', fiscal_start))
            if date_to:
                domain.append(('date', '<=', date_to))
        else:
            if date_from:
                domain.append(('date', '>=', date_from))
            if date_to:
                domain.append(('date', '<=', date_to))

        account_domain = self._account_codes_to_domain(expr.formula)
        if not account_domain:
            # Nothing parsed: return zero rather than summing every account.
            return 0.0
        domain += account_domain

        lines = self.env['account.move.line'].search(domain)
        balance = sum(line.balance for line in lines)
        # A formula whose first term is negative ('-3-4-5-6-7-8') expresses
        # the negated sum of those accounts. Subtract the positive part
        # instead of adding it.
        if expr.formula.lstrip().startswith('-'):
            balance = -balance
        return float_round(balance, precision_digits=2)

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
                        (account_codes if sign == '+' else exclude_codes).append(entry)
                continue

            sign = match.group('sign') or '+'
            if leading_minus:
                # '-3-4-5-6-7-8': every term is an inclusion.
                sign = '+'
            prefix = match.group('prefix')
            excluded = match.group('excluded_prefixes') or ''
            balance_char = match.group('balance_character') or ''

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

    def _eval_aggregation(self, expr, totals, all_expressions):
        """Evaluate an aggregation expression like 'line_A.balance + line_B.balance'."""
        formula = expr.formula or ''
        if formula == 'sum_children':
            return 0.0  # Handled by parent accumulation in JS

        # Parse formula: 'code1.label1 + code2.label2'
        total = 0.0
        terms = re.split(r'[+\-]', re.sub(r'\s+', '', formula))
        operators = re.findall(r'[+\-]', formula)

        if not operators:
            operators = ['+']

        for i, term in enumerate(terms):
            if not term or not '.' in term:
                continue
            op = operators[i] if i < len(operators) else '+'

            # Find the expression by line code + label
            line_code, expr_label = term.split('.', 1)
            target_expr = all_expressions.filtered(
                lambda e: e.report_line_id.code == line_code and e.label == expr_label
            )
            if target_expr:
                val = totals.get((target_expr.id, None), 0.0)
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
        expressions = report.line_ids.expression_ids.filtered(
            lambda e: e.label == 'balance' and e.engine == 'account_codes'
        )
        expressions.write({'date_scope': 'from_beginning'})
        return True
