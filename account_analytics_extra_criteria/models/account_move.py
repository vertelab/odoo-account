# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    analytic_account_ids = fields.Many2many('account.analytic.account', string='Analytic Accounts', readonly=False,
                                            index=True, compute="_compute_analytic_account_ids", store=True,
                                            check_company=True, copy=True)

    invoice_user_id = fields.Many2one('res.users', copy=False, tracking=True, string='Salesperson',
                                      related='move_id.invoice_user_id')

    categ_id = fields.Many2one('product.category', copy=False, tracking=True, string='Salesperson',
                               related='product_id.categ_id')

    @api.depends('product_id', 'account_id', 'partner_id', 'date', 'categ_id')
    def _compute_analytic_account_ids(self):
        for record in self:
            if not record.exclude_from_invoice_tab or not record.move_id.is_invoice(include_receipts=True):
                rec = self.env['account.analytic.default'].account_get_ids(
                    product_id=record.product_id.id,
                    partner_id=record.partner_id.commercial_partner_id.id or record.move_id.partner_id.commercial_partner_id.id,
                    account_id=record.account_id.id,
                    user_id=record.env.uid,
                    date=record.date,
                    company_id=record.move_id.company_id.id,
                    category_id=self._check_product_category(record.categ_id),
                    department_id=self._check_hr_employee(record.invoice_user_id.employee_id.department_id),
                )
                if rec:
                    record.analytic_account_ids = [(6, 0, rec.analytic_id.ids)]

    def _check_product_category(self, categ_id):
        """"
            Step 1: Search account.analytic.default for first product category
            Step 2: if account.analytic.default not found for product category, search account.analytic.default
                    with product category parent
            Step 3: if step 2 not found, repeat step with parent category
        """
        analytic_account_id = False
        product_category_id = categ_id
        if product_category_id and not analytic_account_id:
            analytic_account_id = self.env['account.analytic.default'].account_get_ids(
                category_id=product_category_id.id
            )
            if not analytic_account_id:
                product_category_id = categ_id
                return self._check_product_category(product_category_id['parent_id'])
        return product_category_id.id

    def _check_hr_employee(self, department_id):
        """"
            Step 1: Search account.analytic.default for first hr department
            Step 2: if account.analytic.default not found for hr department, search account.analytic.default
                    with hr department parent
            Step 3: if step 2 not found, repeat step with hr department
        """
        analytic_account_id = False
        hr_department_id = department_id
        if hr_department_id and not analytic_account_id:
            analytic_account_id = self.env['account.analytic.default'].account_get_ids(
                department_id=hr_department_id.id
            )
            if not analytic_account_id:
                hr_department_id = department_id
                return self._check_hr_employee(hr_department_id['parent_id'])
        return hr_department_id.id



