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

    # sets internal reference on all companies and fellowships based on
    # the customer number in Fortnox.
    # Odoo 14: this method is redundant because company_registry doesnt exist in res.partners anymore.
    # There is a module to add it back but since Odoo 14 doesnt use res.partners the same way it might not be worth installing.
    # Furthermore, this method isnt ran anywhere so it might be time wasted to try to make this work.
    def set_internal_reference(self):
        r = self.env.user.company_id.fortnox_request('get', "https://api.fortnox.se/3/customers")
        r = json.loads(r)
        pages = int(r['MetaInformation']['@TotalPages']) + 1

        for page in range(pages):
            url = "https://api.fortnox.se/3/customers?page=" + str(page)
            r = self.env.user.company_id.fortnox_request('get', url)
            r = json.loads(r)
            # time.sleep(0.1)

            for customer in r['Customers']:
                # ~ customer_orgnum = customer.get('OrganisationNumber', False)
                customer_number = customer.get('CustomerNumber', False)
                
                customer_address = customer.get('Address1', False)
                customer_city = customer.get('City', False)
                customer_email = customer.get('Email', False)
                customer_name = customer.get('Name', False)
                customer_phone = customer.get('Phone', False)
                customer_zip = customer.get('ZipCode', False)
                fortnox_fields = [customer_address, customer_city, customer_email, customer_name, customer_phone, customer_zip]
                odoo_fields = ['street', 'city', 'email', 'name', 'phone', 'zip']
                filter_params = []
                for number in range(len(fortnox_fields)):
                    filter_params.append((odoo_fields[number], '=', fortnox_fields[number]))

                #partner = self.env['res.partner'].search([('name', '=', customer_name)])
                partner = self.env['res.partner'].search([('insurance_company_type', '=', 'company'), ('company_registry', '=', customer_orgnum)])

                if customer_orgnum is False:
                    _logger.warn(f"~ ERROR 1: {customer_name} does not have an "
                                 "orgnum in Fortnox, skipping ...")
                elif len(partner) == 0:
                    _logger.warn(f"~ ERROR 3: The orgnum {customer_orgnum} "
                                 "from fortnox was not found in odoo db")
                elif len(partner) > 1:
                    _logger.warn("~ ERROR 2: The orgnum %s from fortnox is not unique in odoo db. Recordset = %s" % (customer_orgnum, partner))
                else:
                    if partner.ref == customer_number:
                        _logger.warn("~ OK 1: %s (id: %s) is already correct" % (customer['Name'], partner.id))
                    else:
                        _logger.warn("~ OK 2: %s's (id: %s) internal reference was set to %s" % (customer['Name'], partner.id, customer['CustomerNumber']))
                        partner.ref = customer_number

    def partner_create(self):
        # Customer (PUT https://api.fortnox.se/3/customers)
        for partner in self:
            _logger.warning(f"CREATING PARTNER {partner=} {partner.commercial_partner_id=} {partner.commercial_partner_id.ref=}")
            if not partner.commercial_partner_id.ref:
                # _logger.warning(f"{self.env.user.company_id=}")
                url = "https://api.fortnox.se/3/customers"
                r = self.env.user.company_id.fortnox_request(
                    'post',
                    url,
                    data={
                        "Customer": {
                            "Address1": partner.street,
                            #"Address2": partner.street2,
                            "City": partner.city,
                            #"Comments": partner.comment,
                            "CountryCode": "SE",
                            "Currency": "SEK",
                            # ~ "CustomerNumber": partner.commercial_partner_id.id,
                            "Email": partner.email or None,
                            "Name": partner.commercial_partner_id.name,
                            #"OrganisationNumber": partner.commercial_partner_id.company_id.company_registry,
                            #"OurReference": partner.commercial_partner_id.user_id.name,
                            "Phone1": partner.commercial_partner_id.phone,
                            "Phone2": None,
                            "PriceList": "A",
                            "ShowPriceVATIncluded": False,
                            # ~ "TermsOfPayment": partner.commercial_partner_id.property_payment_term_id.name,
                            "Type": "COMPANY",
                            #"VATNumber": partner.commercial_partner_id.vat,
                            "VATType": "SEVAT",
                            "WWW": partner.commercial_partner_id.website,
                            "YourReference": partner.name,
                            "ZipCode": partner.zip,
                        }
                    })
                r = json.loads(r)
                partner.commercial_partner_id.ref = r["Customer"]["CustomerNumber"]

    def partner_update(self):
        # Customer (PUT https://api.fortnox.se/3/customers)
        for partner in self:
            _logger.warning(f"UPDATING PARTNER {partner=} {partner.commercial_partner_id=} {partner.commercial_partner_id.ref=}")
            if partner.commercial_partner_id.ref:
                url = "https://api.fortnox.se/3/customers/%s" % partner.commercial_partner_id.ref
                """ r = response """
                r = self.env.user.company_id.fortnox_request(
                    'put',
                    url,
                    data={
                        "Customer": {
                            "Address1": partner.street,
                            #"Address2": partner.street2,
                            "City": partner.city,
                            #"Comments": partner.comment,
                            "CountryCode": "SE",
                            "Currency": "SEK",
                            # ~ "CustomerNumber": partner.commercial_partner_id.ref,
                            "Email": partner.email or None,
                            "Name": partner.commercial_partner_id.name,
                            #"OrganisationNumber": partner.commercial_partner_id.company_registry,
                            #"OurReference": partner.commercial_partner_id.user_id.name,
                            "Phone1": partner.commercial_partner_id.phone,
                            "Phone2": None,
                            "PriceList": "A",
                            "ShowPriceVATIncluded": False,
                            # ~ "TermsOfPayment": partner.commercial_partner_id.property_payment_term_id.name,
                            "Type": "COMPANY",
                            #"VATNumber": partner.commercial_partner_id.vat,
                            "VATType": "SEVAT",
                            "WWW": partner.commercial_partner_id.website,
                            "YourReference": partner.name,
                            "ZipCode": partner.zip,
                        }
                    })
                    
    
    def partner_get(self):
        # Customer (PUT https://api.fortnox.se/3/customers)
        for partner in self:
            url = "https://api.fortnox.se/3/customers/"
            """ r = response """
            r = self.env.user.company_id.fortnox_request(
                'get',
                url,
            )
            _logger.warning(f"{json.loads(r)=}")
