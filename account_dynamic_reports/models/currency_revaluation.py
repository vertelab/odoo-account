# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""Unrealized currency gains/losses on open receivables and payables.

Odoo books *realized* exchange differences automatically when a foreign
currency entry is reconciled (journal "Exchange Difference"). The difference on
entries that are still open is not booked anywhere, and no CE report shows it.
This handler computes it, so the amount can be reviewed — and, at year end,
booked manually by the accountant.

The calculation uses fields that already exist on ``account.move.line``:

    amount_residual           remaining amount in the company currency
    amount_residual_currency  remaining amount in the entry's currency

The unrealized difference is the entry's remaining foreign amount converted at
the report date's rate, minus the amount already booked in the company currency.
"""

from odoo import api, fields, models
from odoo.tools import float_round


class AccountCurrencyRevaluationReportHandler(models.AbstractModel):
    _name = 'account.currency.revaluation.report.handler'
    _description = 'Unrealized Currency Gains/Losses Report Handler'

    RECEIVABLE_TYPES = ('asset_receivable',)
    PAYABLE_TYPES = ('liability_payable',)

    # ------------------------------------------------------------------
    # Expression engine entry point
    # ------------------------------------------------------------------
    @api.model
    def _custom_expression_eval(self, expr, options):
        """Return the value of one report expression.

        Dispatches on ``expr.subformula`` so a single handler can serve all
        columns of the report.
        """
        subformula = expr.subformula or 'adjustment'
        totals = self._get_revaluation_totals(options)
        return totals.get(subformula, 0.0)

    @api.model
    def _custom_expression_eval_excluded(self, expr, options):
        """Amounts on accounts that are excluded from the revaluation.

        Accounts listed in the report's context key ``excluded_account_ids``
        are shown separately instead of being revalued. Empty by default, so
        the line renders as zero until a company configures exclusions.
        """
        excluded = self.env.context.get('excluded_account_ids') or []
        if not excluded:
            return 0.0
        subformula = expr.subformula or 'adjustment'
        totals = self._get_revaluation_totals(options, excluded_account_ids=excluded)
        return totals.get(subformula, 0.0)

    # ------------------------------------------------------------------
    # Core computation
    # ------------------------------------------------------------------
    @api.model
    def _get_report_date(self, options):
        """Report date (the rate date) as a date object."""
        date_to = (options.get('date') or {}).get('date_to')
        if date_to:
            return fields.Date.to_date(date_to)
        return fields.Date.context_today(self)

    @api.model
    def _get_revaluation_totals(self, options, excluded_account_ids=None):
        """Compute the four report amounts.

        Returns a dict with:
            balance_currency   remaining foreign amount
            balance_operation  amount booked in company currency
            balance_current    foreign amount converted at the report date rate
            adjustment         balance_current - balance_operation

        :param excluded_account_ids: when given, only lines on these accounts
            are included (used for the "Excluded Accounts" section).
        """
        company = self.env.company
        company_currency = company.currency_id
        date = self._get_report_date(options)

        lines = self._get_open_foreign_lines(
            options, excluded_account_ids=excluded_account_ids
        )
        if not lines:
            return {
                'balance_currency': 0.0,
                'balance_operation': 0.0,
                'balance_current': 0.0,
                'adjustment': 0.0,
            }

        balance_currency = 0.0
        balance_operation = 0.0
        balance_current = 0.0

        for line in lines:
            line_currency = line.currency_id
            if not line_currency or line_currency == company_currency:
                continue

            foreign_amount = line.amount_residual_currency
            booked = line.amount_residual

            # Convert the remaining foreign amount at the report date's rate.
            rate = line_currency._get_conversion_rate(
                line_currency, company_currency, company, date
            )
            converted = foreign_amount * rate

            balance_currency += foreign_amount
            balance_operation += booked
            balance_current += converted

        return {
            'balance_currency': float_round(balance_currency, precision_digits=2),
            'balance_operation': float_round(balance_operation, precision_digits=2),
            'balance_current': float_round(balance_current, precision_digits=2),
            'adjustment': float_round(balance_current - balance_operation, precision_digits=2),
        }

    @api.model
    def _get_open_foreign_lines(self, options, excluded_account_ids=None):
        """Open receivable/payable lines in a foreign currency.

        :param excluded_account_ids: when given, restrict to these accounts;
            otherwise exclude them.
        """
        company = self.env.company
        domain = [
            ('company_id', '=', company.id),
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', 'in',
             list(self.RECEIVABLE_TYPES + self.PAYABLE_TYPES)),
            ('currency_id', '!=', company.currency_id.id),
            ('amount_residual_currency', '!=', 0.0),
        ]

        if excluded_account_ids:
            domain.append(('account_id', 'in', list(excluded_account_ids)))

        date_to = (options.get('date') or {}).get('date_to')
        if date_to:
            domain.append(('date', '<=', date_to))

        return self.env['account.move.line'].search(domain)

    # ------------------------------------------------------------------
    # Detail rows (used by the report's drill-down)
    # ------------------------------------------------------------------
    @api.model
    def get_revaluation_detail(self, options):
        """Per (currency, account, partner) rows behind the totals.

        Kept separate from the expression engine so the report can show the
        breakdown without recomputing it per column.
        """
        company = self.env.company
        company_currency = company.currency_id
        date = self._get_report_date(options)
        rows = {}

        for line in self._get_open_foreign_lines(options):
            line_currency = line.currency_id
            if not line_currency or line_currency == company_currency:
                continue

            key = (
                line_currency.id,
                line.account_id.id,
                line.partner_id.id or 0,
            )
            row = rows.setdefault(key, {
                'currency': line_currency.name,
                'account': line.account_id.display_name,
                'partner': line.partner_id.display_name or '',
                'balance_currency': 0.0,
                'balance_operation': 0.0,
                'balance_current': 0.0,
                'adjustment': 0.0,
            })

            foreign_amount = line.amount_residual_currency
            rate = line_currency._get_conversion_rate(
                line_currency, company_currency, company, date
            )
            converted = foreign_amount * rate

            row['balance_currency'] += foreign_amount
            row['balance_operation'] += line.amount_residual
            row['balance_current'] += converted

        for row in rows.values():
            row['adjustment'] = float_round(
                row['balance_current'] - row['balance_operation'], precision_digits=2
            )
            row['balance_currency'] = float_round(row['balance_currency'], precision_digits=2)
            row['balance_operation'] = float_round(row['balance_operation'], precision_digits=2)
            row['balance_current'] = float_round(row['balance_current'], precision_digits=2)

        return sorted(rows.values(), key=lambda r: (r['currency'], r['account'], r['partner']))
