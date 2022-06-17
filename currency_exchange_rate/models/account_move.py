# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    currency_rate = fields.Float("Currency Rate", compute='_compute_currency_rate', compute_sudo=True, digits=(12, 6), readonly=True, help='The rate of the currency to the currency of rate 1 applicable at the date of the order')


    @api.depends('invoice_date', 'company_id')
    def _compute_currency_rate(self):
        for order in self:
            if order.period_id and order.period_id.date_start:    
                relevant_date = order.period_id.date_start
            else:
                relevant_date = order.invoice_date
            if not order.company_id:
                order.currency_rate = order.currency_id.with_context(date=relevant_date).rate or 1.0
                continue
            elif order.company_id.currency_id and order.currency_id:  # the following crashes if any one is undefined
                order.currency_rate = self.env['res.currency']._get_conversion_rate(order.currency_id, order.company_id.currency_id, order.company_id, relevant_date or fields.Date.context_today(self))
            else:
                order.currency_rate = 1.0
