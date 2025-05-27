# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _ 
from odoo.exceptions import Warning,UserError

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
                odoo_fields = ['street', 'city', 'email', 'name', 'phone', 'zip', 'commercial_partner_id.fortnox_ref']
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
                    if partner.fortnox_ref == customer_number:
                        _logger.warning("~ OK 1: %s (id: %s) is already correct" % (customer['Name'], partner.id))
                    else:
                        _logger.warning(
                            "~ OK 2: %s's (id: %s) internal reference was set to %s" %
                            (customer['Name'], partner.id, customer['CustomerNumber'])
                        )
                        partner.fortnox_ref = customer_number

    def replace_bool_with_string(self,data):
        ignore = ["ShowPriceVATIncluded"]
        for key in data.keys():
            if key not in ignore and type(data[key]) == type(bool):
                data[key] = ""
        return data

    def get_commercial_entity(self,partner):
        commercial_entity = partner.commercial_partner_id
        if not commercial_entity:
            commercial_entity = partner
        return commercial_entity


    def get_data_dict(self,commercial_entity):

        invoice_contacts = commercial_entity.child_ids.filtered(lambda c: c.type == 'invoice')
        invoice_contact = invoice_contacts[0] if invoice_contacts else False
        
        delivery_contacts = commercial_entity.child_ids.filtered(lambda c: c.type == 'delivery')
        delivery_contact = delivery_contacts[0] if delivery_contacts else False

        VATType = invoice_contact.property_account_position_id.fortnox_vat_type if invoice_contact and invoice_contact.property_account_position_id and invoice_contact.property_account_position_id.fortnox_vat_type else False
        if not VATType:
            VATType = commercial_entity.property_account_position_id.fortnox_vat_type if commercial_entity.property_account_position_id and commercial_entity.property_account_position_id.fortnox_vat_type else "SEVAT"

        data = {
                "Customer": {
                    "Name": commercial_entity.name,
                    "VisitingAddress": commercial_entity.street,
                    "VisitingZipCode": commercial_entity.zip,
                    "VisitingCity": commercial_entity.city,
                    # "VisitingCountry": commercial_entity.country_id.name,
                    "VisitingCountryCode": commercial_entity.country_id.code,
                    "Email": commercial_entity.email or None,

                    "Address1": invoice_contact.street if invoice_contact and invoice_contact.street else commercial_entity.street,
                    "Address2": invoice_contact.street2 if invoice_contact and invoice_contact.street2 else commercial_entity.street2,
                    "ZipCode": invoice_contact.zip if invoice_contact and invoice_contact.zip else commercial_entity.zip, 
                    "City": invoice_contact.city if invoice_contact and invoice_contact.city else commercial_entity.city,
                    # "Country": invoice_contact.country_id.name if invoice_contact else commercial_entity.country_id.name,
                    "CountryCode": invoice_contact.country_id.code if invoice_contact and invoice_contact.country_id.code else commercial_entity.country_id.code,
                    "Phone1": invoice_contact.phone if invoice_contact and invoice_contact.phone else commercial_entity.phone,
                    
                    "DeliveryName": delivery_contact.name if delivery_contact and delivery_contact.name else commercial_entity.name,
                    "DeliveryAddress1": delivery_contact.street if delivery_contact and delivery_contact.street else commercial_entity.street,
                    "DeliveryAddress2": delivery_contact.street2 if delivery_contact and delivery_contact.street2 else commercial_entity.street2,
                    "DeliveryZipCode": delivery_contact.zip if delivery_contact and delivery_contact.zip else commercial_entity.zip,
                    "DeliveryCity": delivery_contact.city if delivery_contact and delivery_contact.city else commercial_entity.city,
                    # "DeliveryCountry": delivery_contact.country_id.name if delivery_contact else commercial_entity.country_id.name,
                    "DeliveryCountryCode": delivery_contact.country_id.code if delivery_contact and delivery_contact.country_id and delivery_contact.country_id.code else commercial_entity.country_id.code,
                    "DeliveryPhone1": delivery_contact.phone if delivery_contact and delivery_contact.phone else commercial_entity.phone,

                    "Phone2": None,
                    "PriceList": "A",
                    "ShowPriceVATIncluded": False,
                    "Type": "COMPANY",
                    "VATType": VATType,
                    "WWW": commercial_entity.website,
                    "YourReference": commercial_entity.name if commercial_entity.type == "contact" else "",
                    "EmailInvoice": invoice_contact.email if invoice_contact and invoice_contact.email else commercial_entity.email,
                }
            }
            
        return self.replace_bool_with_string(data)

    def partner_create(self, company_id):
        for partner in self:
            commercial_entity = self.get_commercial_entity(partner)
            data = self.get_data_dict(commercial_entity)
          
            _logger.warning(
                f"CREATING PARTNER {partner=} {commercial_entity=} {commercial_entity.fortnox_ref=} {data['Customer']['VATType']=}")
           
            if not commercial_entity.fortnox_ref:
                url = "https://api.fortnox.se/3/customers"
                r = company_id.fortnox_request(
                    'post',
                    url,
                    data=data)
                _logger.warning(f"{data=}")
                if r.get("ErrorInformation", {}).get("code") in [2000357]:
                    raise UserError(_("%s has an invalid mail %s") % (partner.name, partner.email))
                _logger.error(f"{r=}")
                commercial_entity.fortnox_ref = r["Customer"]["CustomerNumber"]

    def partner_update(self, company_id):
        for partner in self:
            commercial_entity = self.get_commercial_entity(partner)
            data = self.get_data_dict(commercial_entity)

            _logger.warning(
                f"UPDATING PARTNER {partner=} {commercial_entity=} {commercial_entity.fortnox_ref=} {data['Customer']['VATType']=}")
            _logger.warning(f"{data=}")
            
            if commercial_entity.fortnox_ref:
                url = "https://api.fortnox.se/3/customers/%s" % partner.commercial_partner_id.fortnox_ref
                company_id.fortnox_request('put',url,data=data)

    def partner_get(self, company_id):
        for partner in self:
            url = "https://api.fortnox.se/3/customers/"
            """ r = response """
            company_id.fortnox_request(
                'get',
                url,
            )
