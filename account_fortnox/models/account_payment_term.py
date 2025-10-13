# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
import logging
import json
import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

BASE_URL = 'https://api.fortnox.se'


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    fortnox_url = fields.Char()
    fortnox_code = fields.Char()
    fortnox_description = fields.Char()

    def payment_term_create(self, company_id = False):
        self.get_all_payment_terms()
        
        # ~ if not company_id:
            # ~ company_id = self.env.company
        # ~ for payment_term in self:
            # ~ if not payment_term.fortnox_url:
                # ~ url = BASE_URL + "/3/termsofpayments"
                # ~ r = company_id.fortnox_request(
                    # ~ 'post',
                    # ~ url,
                    # ~ data={
                        # ~ "TermsOfPayment": 
                        # ~ {
                            # ~ #"@url": "string",
                            # ~ "Code": "77",
                            # ~ "Description": "Description"
                        # ~ }
                    # ~ })
                # ~ if r.get('ErrorInformation', False):
                    # ~ raise UserError(str(r.get('ErrorInformation')))
                # ~ _logger.warning(f"{r=}")
                #partner.commercial_partner_id.fortnox_ref = r["Customer"]["CustomerNumber"]
    def get_all_payment_terms(self):
        company_id = self.env.company
        url = BASE_URL + "/3/termsofpayments"
        r = company_id.fortnox_request(
                    'get',
                    url,
                    data={
                        "TermsOfPayment": 
                        {
                        }
                    })
        raise UserError(str(r))
