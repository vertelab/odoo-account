# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import Warning

import requests
import json
import time

import logging

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'

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

            for customer in r['Customers']:
                customer_number = customer.get('CustomerNumber', False)

                customer_address = customer.get('Address1', False)
                customer_city = customer.get('City', False)
                customer_email = customer.get('Email', False)
                customer_name = customer.get('Name', False)
                customer_phone = customer.get('Phone', False)
                customer_zip = customer.get('ZipCode', False)
                fortnox_fields = [
                    customer_address, customer_city, customer_email, customer_name, customer_phone,
                    customer_zip, customer_number
                ]
                odoo_fields = ['street', 'city', 'email', 'name', 'phone', 'zip', 'commercial_partner_id.ref']
                filter_params = []
                for number in range(len(fortnox_fields)):
                    if not fortnox_fields[number] == False:
                        filter_params.append((odoo_fields[number], '=', fortnox_fields[number]))

                partner = self.env['res.partner'].search(filter_params)
                if len(partner) == 0:
                    _logger.warning(f"~ ERROR 3: No customer from fortnox was found in odoo db")
                elif len(partner) > 1:
                    _logger.warning(
                        "~ ERROR 2: Several customers from fortnox with the same ref found in odoo db. Recordset = %s"
                        % partner
                    )
                else:
                    if partner.ref == customer_number:
                        _logger.warning("~ OK 1: %s (id: %s) is already correct" % (customer['Name'], partner.id))
                    else:
                        _logger.warning(
                            "~ OK 2: %s's (id: %s) internal reference was set to %s" %
                            (customer['Name'], partner.id, customer['CustomerNumber'])
                        )
                        partner.ref = customer_number

    def partner_create(self):
        for partner in self:
            _logger.warning(
                f"CREATING PARTNER {partner=} {partner.commercial_partner_id=} {partner.commercial_partner_id.ref=}")
            if not partner.commercial_partner_id.ref:
                url = "https://api.fortnox.se/3/customers"
                r = self.env.user.company_id.fortnox_request(
                    'post',
                    url,
                    data={
                        "Customer": {
                            "Address1": partner.street,
                            "City": partner.city,
                            "CountryCode": "SE",
                            "Currency": "SEK",
                            "Email": partner.email or None,
                            "Name": partner.commercial_partner_id.name,
                            "Phone1": partner.commercial_partner_id.phone,
                            "Phone2": None,
                            "PriceList": "A",
                            "ShowPriceVATIncluded": False,
                            "Type": "COMPANY",
                            "VATType": "SEVAT",
                            "WWW": partner.commercial_partner_id.website,
                            "YourReference": partner.name,
                            "ZipCode": partner.zip,
                        }
                    })
                partner.commercial_partner_id.ref = r["Customer"]["CustomerNumber"]

    def partner_update(self):
        for partner in self:
            _logger.warning(
                f"UPDATING PARTNER {partner=} {partner.commercial_partner_id=} {partner.commercial_partner_id.ref=}")
            if partner.commercial_partner_id.ref:
                url = "https://api.fortnox.se/3/customers/%s" % partner.commercial_partner_id.ref
                self.env.user.company_id.fortnox_request(
                    'put',
                    url,
                    data={
                        "Customer": {
                            "Address1": partner.street,
                            "City": partner.city,
                            "CountryCode": "SE",
                            "Currency": "SEK",
                            "Email": partner.email or None,
                            "Name": partner.commercial_partner_id.name,
                            "Phone1": partner.commercial_partner_id.phone,
                            "Phone2": None,
                            "PriceList": "A",
                            "ShowPriceVATIncluded": False,
                            "Type": "COMPANY",
                            "VATType": "SEVAT",
                            "WWW": partner.commercial_partner_id.website,
                            "YourReference": partner.name,
                            "ZipCode": partner.zip,
                        }
                    })

    def partner_get(self):
        for partner in self:
            url = "https://api.fortnox.se/3/customers/"
            """ r = response """
            self.env.user.company_id.fortnox_request(
                'get',
                url,
            )
