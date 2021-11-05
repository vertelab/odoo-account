# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAnalyticDefault(models.Model):
    _inherit = "account.analytic.default"

    product_category_id = fields.Many2one('product.category', string="Product Category")
    hr_department_id = fields.Many2one('hr.department', string="Employee Department")

    @api.model
    def account_get_ids(self, product_id=None, partner_id=None, account_id=None, user_id=None, date=None, company_id=None, category_id=None, department_id=None):
        domain = []
        if product_id:
            domain += ['|', ('product_id', '=', product_id)]
        domain += [('product_id', '=', False)]
        if partner_id:
            domain += ['|', ('partner_id', '=', partner_id)]
        domain += [('partner_id', '=', False)]
        if account_id:
            domain += ['|', ('account_id', '=', account_id)]
        domain += [('account_id', '=', False)]
        if company_id:
            domain += ['|', ('company_id', '=', company_id)]
        domain += [('company_id', '=', False)]
        if user_id:
            domain += ['|', ('user_id', '=', user_id)]
        domain += [('user_id', '=', False)]
        if category_id:
            domain += ['|', ('product_category_id', '=', category_id)]
        domain += [('product_category_id', '=', False)]
        print("category_id", category_id)
        if department_id:
            domain += ['|', ('hr_department_id', '=', department_id)]
        domain += [('hr_department_id', '=', False)]
        if date:
            domain += ['|', ('date_start', '<=', date), ('date_start', '=', False)]
            domain += ['|', ('date_stop', '>=', date), ('date_stop', '=', False)]
        return self.search(domain)

    @api.model
    def account_get_product_category_ids(self, category_id=None):
        domain = []
        if category_id:
            domain += ['|', ('product_category_id', '=', category_id)]
        domain += [('product_category_id', '=', False)]
        return self.search(domain)

    @api.model
    def account_get_hr_department_ids(self, department_id=None):
        domain = []
        if department_id:
            domain += ['|', ('hr_department_id', '=', department_id)]
        domain += [('hr_department_id', '=', False)]
        return self.search(domain)
