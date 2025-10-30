# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

BASE_URL = 'https://api.fortnox.se'


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    fortnox_url = fields.Char(string='Fortnox URL')
    fortnox_code = fields.Char(string='Fortnox Code')
    fortnox_description = fields.Char(string='Fortnox Description')

    def payment_term_create(self, company_id=None):
        """
        Create payment terms in Fortnox.
        Currently only fetches existing payment terms from Fortnox.
        """
        if not company_id:
            company_id = self.env.company

        self.get_all_payment_terms(company_id)

    def get_all_payment_terms(self, company_id=None):
        """Fetch all payment terms from Fortnox API."""
        if not company_id:
            company_id = self.env.company

        url = f"{BASE_URL}/3/termsofpayments"

        response = company_id.fortnox_request('GET', url, data={})

        _logger.info(f"Fetched payment terms from Fortnox: {response}")

        # TODO: Process and store payment terms instead of raising error
        raise UserError(f"Payment terms from Fortnox: {response}")