# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountReportColumn(models.Model):
    """Give report columns a date scope.

    Core ``account.report.column`` only says *what* to show (an expression
    label), not *for which period*. A Swedish balance sheet needs three
    columns side by side -- opening balance, period movement and closing
    balance -- and they differ only by their date interval. This module adds
    that interval to the column, so the engine can compute one value per
    column group instead of one value per expression.
    """

    _inherit = 'account.report.column'

    date_from = fields.Date(
        string='Date From',
        help='Start of the period this column shows. Empty means "from the '
             'beginning of time", which is what an opening-balance column needs.',
    )
    date_to = fields.Date(
        string='Date To',
        help='End of the period this column shows. Empty means "until today".',
    )
    date_scope = fields.Selection(
        selection=[
            ('strict_range', 'Period only'),
            ('from_beginning', 'From the beginning'),
            ('from_fiscalyear', 'From the start of the fiscal year'),
        ],
        string='Date Scope',
        default='strict_range',
        required=True,
        help='Which entries the column counts. "Period only" is the default and '
             'what VAT boxes need. "From the beginning" includes the opening '
             'balance, which is what a balance-sheet column needs.',
    )
