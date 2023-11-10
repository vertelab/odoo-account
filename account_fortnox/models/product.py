# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo import api, fields, models
from odoo.exceptions import Warning
from odoo.tools.safe_eval import safe_eval, wrap_module

import datetime
import time

from pytz import timezone
import logging

import requests

_logger = logging.getLogger(__name__)

# build dateutil helper, starting with the relevant *lazy* imports
import dateutil
import base64
import json


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    membership_product_ids = fields.Many2many(comodel_name='product.template', relation='membership_product_rel',
                                              column1='product_id', column2='member_product_id',
                                              string='Membership Products',
                                              domain="[('membership','=',True), ('type', '=', 'service')]")

    # Python code
    membership_code = fields.Text(string='Python Code', groups='base.group_system',
                                  default="""# Available variables:
#  - env: Odoo Environment on which the action is triggered
#  - model: Odoo Model of the record on which the action is triggered; is a void recordset
#  - record: record on which the action is triggered; may be void
#  - records: recordset of all records on which the action is triggered in multi-mode; may be void
#  - time, datetime, dateutil, timezone: useful Python libraries
#  - log: log(message, level='info'): logging function to record debug information in ir.logging table
#  - Warning: Warning Exception to use with raise
#  - product; membership product
#  - partner: partner to invoice
# To return an amount and qty, assign: \n
#        amount =  <something>
#        qty = <something>\n\n\n\n""",
                                  help="Write Python code that holds advanced calcultations for amount and quatity")


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def membership_get_amount_qty(self, partner):
        allowed_time_attributes = ['time', 'sleep', 'strftime']
        allowed_datetime_attributes = ['time', 'datetime', 'date']
        allowed_dateutil_attributes = ['parser', 'relativedelta', 'tz']

        eval_context = {
            'uid': self._uid,
            'user': self.env.user,
            'time': wrap_module(time, allowed_time_attributes),
            'datetime': wrap_module(datetime, allowed_datetime_attributes),
            'dateutil': wrap_module(dateutil,
                                    {mod: getattr(dateutil, mod).__all__ for mod in allowed_dateutil_attributes}),
            'timezone': timezone,
            'b64encode': base64.b64encode,
            'b64decode': base64.b64decode,
            'partner': partner,
            'product': self,
        }
        safe_eval(self.membership_code.strip(), eval_context, mode="exec", nocopy=True)
        return eval_context.get('amount', self.list_price), eval_context.get('qty', 1.0)

    def article_update(self, company_id):
        _logger.warning(f"{company_id=}")
        for product in self:
            if not product.default_code:
                res = company_id.fortnox_request(
                    'post',
                    'https://api.fortnox.se/3/articles',
                    data={
                        'Article': {
                            'Description': product.name,
                            #'ArticleNumber': product.default_code,
                        }
                    })
                _logger.warning(f"{res=}")
                default_code = res.get('Article', {}).get('ArticleNumber')
                product.default_code = default_code
                
                #raise UserError('Missing default code for product')

            url = "https://api.fortnox.se/3/articles/%s" % product.default_code
            r = company_id.fortnox_request(
                'get', url, raise_error=False)

            default_code = r.get('Article', {}).get('ArticleNumber')
            if default_code == product.default_code:
                try:
                    url = f"https://api.fortnox.se/3/articles/{product.default_code}"
                    r = company_id.fortnox_request(
                        'put',
                        url,
                        data={
                            "Article": {
                                "Description": product.name,
                            }
                        })
                except requests.exceptions.RequestException as e:
                    _logger.exception(f'Request error in article update: {e}')
            else:
                company_id.fortnox_request(
                    'post',
                    'https://api.fortnox.se/3/articles',
                    data={
                        'Article': {
                            'Description': product.name,
                            'ArticleNumber': product.default_code,
                        }
                    })


class ResPartner(models.Model):
    _inherit = "res.partner"

    def create_membership_invoice(self, product, amount):
        """ Create Customer Invoice of Membership for partners.
        @param datas: datas has dictionary value which consist Id of Membership product and Cost Amount of Membership.
                      datas = {'membership_product_id': None, 'amount': None}
        """
        invoice_list = super(ResPartner, self).create_membership_invoice(product=product, amount=amount)
        # Add extra products
        for move in invoice_list:
            for line in move.invoice_line_ids:
                for member_product in line.product_id.membership_product_ids:
                    # create a record in cache, apply onchange then revert back to a dictionary
                    move_line = self.env['account.move.line'].new(
                        {'product_id': member_product.id, 'price_unit': member_product.lst_price, 'move_id': move.id})
                    move_line._onchange_product_id()
                    line_values = move_line._convert_to_write({name: move_line[name] for name in move_line._cache})
                    line_values['name'] = member_product.name
                    line_values[
                        'account_id'] = member_product.property_account_income_id.id if member_product.property_account_income_id else \
                    self.env['account.account'].search(
                        [('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)])[0].id
                    move.write({'invoice_line_ids': [(0, 0, line_values)]})
        # Calculate amount and qty
        for move in invoice_list:
            for line in move.invoice_line_ids:
                if line.product_id.membership_code:
                    line.price_unit, line.quantity = line.product_id.membership_get_amount_qty(move.partner_id.id)
        return invoice_list
