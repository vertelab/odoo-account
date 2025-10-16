# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import logging
import time

import dateutil
import requests
from pytz import timezone

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval, wrap_module

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    membership_product_ids = fields.Many2many(
        comodel_name='product.template',
        relation='membership_product_rel',
        column1='product_id',
        column2='member_product_id',
        string='Membership Products',
        domain="[('membership','=',True), ('type', '=', 'service')]"
    )

    membership_code = fields.Text(
        string='Python Code',
        groups='base.group_system',
        default="""# Available variables:
#  - env: Odoo Environment on which the action is triggered
#  - model: Odoo Model of the record on which the action is triggered; is a void recordset
#  - record: record on which the action is triggered; may be void
#  - records: recordset of all records on which the action is triggered in multi-mode; may be void
#  - time, datetime, dateutil, timezone: useful Python libraries
#  - log: log(message, level='info'): logging function to record debug information in ir.logging table
#  - Warning: Warning Exception to use with raise
#  - product: membership product
#  - partner: partner to invoice
# To return an amount and qty, assign:
#     amount = <something>
#     qty = <something>
""",
        help="Write Python code that holds advanced calculations for amount and quantity"
    )


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
        """Synchronize product articles with Fortnox API."""
        _logger.info(f"Starting article update for company_id={company_id.id}")

        for product in self:
            if not product.default_code:
                product._create_fortnox_article(company_id)

            if product.default_code:
                product._sync_fortnox_article(company_id)

    def _create_fortnox_article(self, company_id, article_number=None):
        """Create a new article in Fortnox and optionally update product with ArticleNumber."""
        try:
            article_data = {'Description': self.name}
            if article_number:
                article_data['ArticleNumber'] = article_number

            response = company_id.fortnox_request(
                'post',
                'https://api.fortnox.se/3/articles',
                data={'Article': article_data}
            )

            returned_article_number = response.get('Article', {}).get('ArticleNumber')
            if returned_article_number:
                if not article_number:
                    self.default_code = returned_article_number
                _logger.info(
                    f"Created Fortnox article with ArticleNumber={returned_article_number} for product {self.id}")
            else:
                _logger.warning(f"No ArticleNumber returned for product {self.id}")

        except requests.exceptions.RequestException as e:
            _logger.exception(f"Failed to create Fortnox article for product {self.id}: {e}")

    def _sync_fortnox_article(self, company_id):
        """Update existing Fortnox article or create if not found."""
        url = f"https://api.fortnox.se/3/articles/{self.default_code}"

        try:
            response = company_id.fortnox_request('get', url, raise_error=False)
            article_number = response.get('Article', {}).get('ArticleNumber')

            if article_number == self.default_code:
                self._update_fortnox_article(company_id)
            else:
                self._create_fortnox_article(company_id, self.default_code)

        except requests.exceptions.RequestException as e:
            _logger.exception(f"Failed to sync Fortnox article for product {self.id}: {e}")

    def _update_fortnox_article(self, company_id):
        """Update an existing Fortnox article."""
        url = f"https://api.fortnox.se/3/articles/{self.default_code}"

        try:
            company_id.fortnox_request(
                'put',
                url,
                data={
                    "Article": {
                        "Description": self.name,
                    }
                }
            )
            _logger.info(f"Updated Fortnox article {self.default_code} for product {self.id}")

        except requests.exceptions.RequestException as e:
            _logger.exception(f"Failed to update Fortnox article {self.default_code}: {e}")