# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import requests

from odoo import models

_logger = logging.getLogger(__name__)

BASE_URL = 'https://api.fortnox.se'


class ProductProduct(models.Model):
    _inherit = 'product.product'

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
                f'{BASE_URL}/3/articles',
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
        url = f"{BASE_URL}/3/articles/{self.default_code}"

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
        url = f"{BASE_URL}/3/articles/{self.default_code}"

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
