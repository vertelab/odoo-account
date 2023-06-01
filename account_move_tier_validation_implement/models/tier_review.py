# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
import pytz
from datetime import datetime


class TierReview(models.Model):
    _inherit = "tier.review"

    resource_date = fields.Date(string="Resource Date", compute="_compute_resource_data")
    resource_currency_id = fields.Many2one("res.currency", string="Resource Currency", compute="_compute_resource_data")
    resource_amount = fields.Monetary(string="Resource Amount", compute="_compute_resource_data",
                                      currency_field='resource_currency_id')
    resource_partner_id = fields.Many2one("res.partner", string="Resource Partner", compute="_compute_resource_data")

    @api.depends("model", "res_id")
    def _compute_resource_data(self):
        for rec in self:
            res_obj = self.env[rec.model].browse(rec.res_id)
            if res_obj.fields_get().get('invoice_date', False):
                rec.resource_date = res_obj.invoice_date
                rec.resource_amount = res_obj.amount_total_loc
            elif res_obj.fields_get().get('invoice_date_due', False):
                rec.resource_date = res_obj.invoice_date_due
                rec.resource_amount = res_obj.amount_total_loc
            elif res_obj.fields_get().get('date_order', False):
                rec.resource_date = res_obj.date_order
                rec.resource_amount = res_obj.amount_total
            else:
                rec.resource_date = False
                rec.resource_amount = False
            rec.resource_partner_id = res_obj.partner_id.id
            rec.resource_currency_id = res_obj.currency_id.id
