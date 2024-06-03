# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import requests
import json
import time

import logging

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'

    fortnox_ref = fields.Char(string='Fortnox Customer ID', index=True, company_dependent=True)

    # sets internal reference on all companies and fellowships based on the customer number in Fortnox. Odoo 14: this
    # method is redundant because company_registry doesn't exist in res.partners anymore. There is a module to add it
    # back but since Odoo 14 doesn't use res.partners the same way it might not be worth installing. Furthermore,
    # this method isn't ran anywhere so it might be time wasted to try to make this work.
    def set_internal_reference(self):
        r = self.env.user.company_id.fortnox_request('get', "https://api.fortnox.se/3/customers")
        pages = int(r['MetaInformation']['@TotalPages']) + 1

        for page in range(pages):
            url = "https://api.fortnox.se/3/customers?page=" + str(page)
            r = self.env.user.company_id.fortnox_request('get', url)
            _logger.warning(f"{r['Customers']=}")
            for customer in r['Customers']:
                #_logger.warning(f"{customer=}")
                customer_number = customer.get('CustomerNumber', False)
                if customer_number:
                   customer_number_partner = self.env['res.partner'].search([('fortnox_ref',"=",customer_number)])
                   if customer_number_partner:
                      _logger.warning(f"~ ERROR 3: Partner Found with matching customer number {customer_number=} {customer_number_partner=} {customer_number_partner.name=}")
                      continue
                
                customer_address = customer.get('Address1', False)
                customer_city = customer.get('City', False)
                customer_email = customer.get('Email', False)
                customer_name = customer.get('Name', False)
                customer_phone = customer.get('Phone', False)
                customer_zip = customer.get('ZipCode', False)
                fortnox_fields2 = [
                    customer_address, customer_city, customer_email, customer_name, customer_phone,
                    customer_zip
                ]
                
                fortnox_fields = []
                for fortnox_field in fortnox_fields2:
                    if fortnox_field == "0" or fortnox_field == "":
                       _logger.warning(f"{fortnox_field=}")
                       fortnox_field = False
                    fortnox_fields.append(fortnox_field)


                odoo_fields = ['street', 'city', 'email', 'name', 'phone', 'zip']
                filter_params = [('commercial_partner_id.fortnox_ref','=',False)]
                for number in range(len(fortnox_fields)):
                    if not fortnox_fields[number] == False:
                        filter_params.append((odoo_fields[number], '=', fortnox_fields[number]))
                
                partner = self.env['res.partner'].search(filter_params)
                if len(partner) == 1:
                    _logger.warning(f"~ Found contact with {filter_params=} that is missing an fortnox_ref. Setting ref to {customer_number=}")
                    partner.fortnox_ref = customer_number

    def partner_create(self, company_id):
        for partner in self:
            _logger.warning(
                f"CREATING PARTNER {partner=} {partner.commercial_partner_id=} {partner.commercial_partner_id.fortnox_ref=}")
            if not partner.commercial_partner_id.fortnox_ref:
                url = "https://api.fortnox.se/3/customers"
                r = company_id.fortnox_request(
                    'post',
                    url,
                    data={
                        "Customer": {
                            "Address1": partner.commercial_partner_id.street,
                            "City": partner.commercial_partner_id.city,
                            "CountryCode": "SE",
                            "Currency": "SEK",
                            "Email": partner.commercial_partner_id.email or None,
                            "Name": partner.commercial_partner_id.name,
                            "Phone1": partner.commercial_partner_id.phone,
                            "Phone2": None,
                            "PriceList": "A",
                            "ShowPriceVATIncluded": False,
                            "Type": "COMPANY",
                            "VATType": "SEVAT",
                            "WWW": partner.commercial_partner_id.website,
                            "YourReference": partner.commercial_partner_id.name,
                            "ZipCode": partner.commercial_partner_id.zip,
                        }
                    })
                if r.get("ErrorInformation", {}).get("code") in [2000357]:
                    raise UserError(_(f"{partner.name} has an invalid mail {partner.email}"))
                partner.commercial_partner_id.fortnox_ref = r["Customer"]["CustomerNumber"]

    def partner_update(self, company_id):
        for partner in self:
            _logger.warning(
                f"UPDATING PARTNER {partner=} {partner.commercial_partner_id=} {partner.commercial_partner_id.fortnox_ref=}")
            if partner.commercial_partner_id.fortnox_ref:
                url = "https://api.fortnox.se/3/customers/%s" % partner.commercial_partner_id.fortnox_ref
                company_id.fortnox_request(
                    'put',
                    url,
                    data={
                        "Customer": {
                            "Address1": partner.commercial_partner_id.street,
                            "City": partner.commercial_partner_id.city,
                            "CountryCode": "SE",
                            "Currency": "SEK",
                            "Email": partner.commercial_partner_id.email or None,
                            "Name": partner.commercial_partner_id.name,
                            "Phone1": partner.commercial_partner_id.phone,
                            "Phone2": None,
                            "PriceList": "A",
                            "ShowPriceVATIncluded": False,
                            "Type": "COMPANY",
                            "VATType": "SEVAT",
                            "WWW": partner.commercial_partner_id.website,
                            "YourReference": partner.commercial_partner_id.name,
                            "ZipCode": partner.commercial_partner_id.zip,
                        }
                    })

    def partner_get(self, company_id):
        for partner in self:
            url = "https://api.fortnox.se/3/customers/"
            """ r = response """
            company_id.fortnox_request(
                'get',
                url,
            )
