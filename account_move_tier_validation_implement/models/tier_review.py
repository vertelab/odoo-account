# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.osv import expression
import pytz
from datetime import datetime


class TierReview(models.Model):
    _inherit = "tier.review"

    resource_date = fields.Date(string="Resource Date", compute="_compute_resource_data")
    resource_currency_id = fields.Many2one("res.currency", string="Resource Currency", compute="_compute_resource_data")
    resource_amount = fields.Monetary(string="Resource Amount", compute="_compute_resource_data",
                                      currency_field='resource_currency_id')
    resource_partner_id = fields.Many2one("res.partner", string="Resource Partner", compute="_compute_resource_data", store=True)
    invoice_due_date = fields.Date(string="Invoice Due Date", compute="_compute_resource_data")

    def _search_resource_name(self, operator, value):
        print(operator)
        return [('copy_resource_name', operator, value)]

    resource_name = fields.Char(
        compute="_compute_resource_ref",
        compute_sudo=True,
        search='_search_resource_name',
    )
    copy_resource_name = fields.Char(
        compute_sudo=True,
        string="Resource Name",
        compute="_compute_resource_name", store=True)

    @api.depends("model", "res_id")
    def _compute_resource_data(self):
        for rec in self:
            res_obj = self.env[rec.model].browse(rec.res_id)
            if res_obj.fields_get().get('invoice_date', False):
                rec.resource_date = res_obj.invoice_date
                rec.resource_amount = res_obj.amount_total_loc
            elif res_obj.fields_get().get('date_order', False):
                rec.resource_date = res_obj.date_order
                rec.resource_amount = res_obj.amount_total
            else:
                rec.resource_date = False
                rec.resource_amount = False
            rec.resource_partner_id = res_obj.partner_id.id
            rec.resource_currency_id = res_obj.currency_id.id

            if res_obj.fields_get().get('invoice_date_due', False):
                rec.invoice_due_date = res_obj.invoice_date_due
            else:
                rec.invoice_due_date = False

    @api.depends("model", "res_id", "resource_ref", "resource_type")
    def _compute_resource_ref(self):
        for rec in self:
            if rec.model and rec.res_id:
                rec.resource_ref = (
                    "%s,%s" % (rec.model, rec.res_id) if rec.res_id else False
                )
                rec.resource_type = rec.model
            else:
                rec.resource_ref = False
                rec.resource_type = False

            if rec.resource_ref:
                rec.resource_name = rec.resource_ref.display_name
                rec.next_review = rec.resource_ref.next_review
            else:
                rec.resource_name = False
                rec.next_review = False

    @api.depends("resource_ref")
    def _compute_resource_name(self):
        for rec in self:
            rec.copy_resource_name = rec.resource_name

