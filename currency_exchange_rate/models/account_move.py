# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    currency_rate = fields.Float(
        "Currency Rate",
        compute='_compute_currency_rate',
        compute_sudo=True,
        digits=(12, 6),
        readonly=True,
        help='The rate of the currency to the currency of rate 1 applicable at the invoice date',
    )

    @api.depends('invoice_date', 'date', 'company_id', 'currency_id')
    def _compute_currency_rate(self):
        for order in self:
            # account_fiscal_year_vrtl derives the period from the move date
            # (account.period.date2period); there is no stored period_id to
            # read a date_start from, so the move date is the reference.
            relevant_date = order.invoice_date or order.date
            if not order.company_id:
                order.currency_rate = order.currency_id.with_context(date=relevant_date).rate or 1.0
            elif order.company_id.currency_id and order.currency_id:
                order.currency_rate = self.env['res.currency']._get_conversion_rate(
                    order.currency_id,
                    order.company_id.currency_id,
                    order.company_id,
                    relevant_date or fields.Date.context_today(self),
                )
            else:
                order.currency_rate = 1.0
