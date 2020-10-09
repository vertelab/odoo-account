# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import Warning

import requests
import json

import logging
_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'
    

#FIXME:make fortnox_update auto-updating.
    @api.multi
    def fortnox_update(self):
        # Customer (PUT https://api.fortnox.se/3/customers)
        for partner in self:
            if not partner.commercial_partner_id.ref:
                
                url = "https://api.fortnox.se/3/customers"
                """ r = response """
                r = self.env['res.company'].name.fortnox_request('post', url,
                    data={
                        "Customer": {
                            "Address1": partner.street,
                            "Address2": partner.street2,
                            "City": partner.city,
                            "Comments": partner.comment,
                            "CountryCode": "SE",
                            "Currency": "SEK",
                            # ~ "CustomerNumber": partner.commercial_partner_id.id,
                            "Email": partner.email,
                            "Name": partner.commercial_partner_id.name,
                            "OrganisationNumber": partner.commercial_partner_id.company_registry,
                            "OurReference": partner.commercial_partner_id.user_id.name,
                            "Phone1": partner.commercial_partner_id.phone,
                            "Phone2": None,
                            "PriceList": "A",
                            "ShowPriceVATIncluded": False,
                            "TermsOfPayment": partner.commercial_partner_id.property_payment_term_id.name,
                            "Type": "COMPANY",
                            "VATNumber": partner.commercial_partner_id.vat,
                            "VATType": "SEVAT",
                            "WWW": partner.commercial_partner_id.website,
                            "YourReference": partner.name,
                            "ZipCode": partner.zip,
                        }
                    })
            if partner.commercial_partner_id.ref:
                url = "https://api.fortnox.se/3/customers/%s" % partner.commercial_partner_id.ref
                """ r = response """
                r = self.env['res.company'].name.fortnox_request('put', url,
                    data={
                        "Customer": {
                            "Address1": partner.street,
                            "Address2": partner.street2,
                            "City": partner.city,
                            "Comments": partner.comment,
                            "CountryCode": "SE",
                            "Currency": "SEK",
                            # ~ "CustomerNumber": partner.commercial_partner_id.id,
                            "Email": partner.email,
                            "Name": partner.commercial_partner_id.name,
                            "OrganisationNumber": partner.commercial_partner_id.company_registry,
                            "OurReference": partner.commercial_partner_id.user_id.name,
                            "Phone1": partner.commercial_partner_id.phone,
                            "Phone2": None,
                            "PriceList": "A",
                            "ShowPriceVATIncluded": False,
                            "TermsOfPayment": partner.commercial_partner_id.property_payment_term_id.name,
                            "Type": "COMPANY",
                            "VATNumber": partner.commercial_partner_id.vat,
                            "VATType": "SEVAT",
                            "WWW": partner.commercial_partner_id.website,
                            "YourReference": partner.name,
                            "ZipCode": partner.zip,
                        }
                    })
            
            r = json.loads(r)
            # ~ raise Warning(str(r))
            partner.commercial_partner_id.ref = r["Customer"]["CustomerNumber"]
    
            return r  
            
    
