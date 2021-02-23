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
	
	@api.multi
	def check_fortnox_customer_number(self):
		url = "https://api.fortnox.se/3/customers"
		r = self.env.user.company_id.fortnox_request('get', url)
		r = json.loads(r)
		pages = int(r['MetaInformation']['@TotalPages']) + 1
		
		for partner in self:
			for page in range(pages):
				url = "https://api.fortnox.se/3/customers?page=" + str(page)
				_logger.warn("Haze url %s" % url)
				r = self.env.user.company_id.fortnox_request('get', url)
				r  = json.loads(r)
				customers = r['Customers']
				for customer in customers:
					_logger.warn("HAZE: %s - %s" % (customer['Name'], customer['OrganisationNumber']))
					if partner.commercial_partner_id.company_registry == customer.get('OrganisationNumber', False):
						partner.commercial_partner_id.ref = customer['CustomerNumber']

	def partner_create(self):
		# Customer (PUT https://api.fortnox.se/3/customers)
		for partner in self:
			if not partner.commercial_partner_id.ref:
				# ~ try:
				url = "https://api.fortnox.se/3/customers"
				""" r = response """
				r = self.env.user.company_id.fortnox_request('post', url,
					data={
						"Customer": {
							"Address1": partner.street,
							"Address2": partner.street2,
							"City": partner.city,
							"Comments": partner.comment,
							"CountryCode": "SE",
							"Currency": "SEK",
							# ~ "CustomerNumber": partner.commercial_partner_id.id,
							"Email": partner.email or None,
							"Name": partner.commercial_partner_id.name,
							"OrganisationNumber": partner.commercial_partner_id.company_registry,
							"OurReference": partner.commercial_partner_id.user_id.name,
							"Phone1": partner.commercial_partner_id.phone,
							"Phone2": None,
							"PriceList": "A",
							"ShowPriceVATIncluded": False,
							# ~ "TermsOfPayment": partner.commercial_partner_id.property_payment_term_id.name,
							"Type": "COMPANY",
							"VATNumber": partner.commercial_partner_id.vat,
							"VATType": "SEVAT",
							"WWW": partner.commercial_partner_id.website,
							"YourReference": partner.name,
							"ZipCode": partner.zip,
						}
					})
			r = json.loads(r)
			partner.commercial_partner_id.ref = r["Customer"]["CustomerNumber"]
			_logger.warn('Haze %s' % partner.commercial_partner_id.ref )
			return requests.get(url).json()
#FIXME:make fortnox_update auto-updating.
	@api.multi
	def partner_update(self):
		# Customer (PUT https://api.fortnox.se/3/customers)
		for partner in self:
			if partner.commercial_partner_id.ref:
				url = "https://api.fortnox.se/3/customers/%s" % partner.commercial_partner_id.ref
				""" r = response """
				r = self.env.user.company_id.fortnox_request('put', url,
					data={
						"Customer": {
							"Address1": partner.street,
							"Address2": partner.street2,
							"City": partner.city,
							"Comments": partner.comment,
							"CountryCode": "SE",
							"Currency": "SEK",
							# ~ "CustomerNumber": partner.commercial_partner_id.ref,
							"Email": partner.email or None,
							"Name": partner.commercial_partner_id.name,
							"OrganisationNumber": partner.commercial_partner_id.company_registry,
							"OurReference": partner.commercial_partner_id.user_id.name,
							"Phone1": partner.commercial_partner_id.phone,
							"Phone2": None,
							"PriceList": "A",
							"ShowPriceVATIncluded": False,
							# ~ "TermsOfPayment": partner.commercial_partner_id.property_payment_term_id.name,
							"Type": "COMPANY",
							"VATNumber": partner.commercial_partner_id.vat,
							"VATType": "SEVAT",
							"WWW": partner.commercial_partner_id.website,
							"YourReference": partner.name,
							"ZipCode": partner.zip,
						}
					})
					
			
			r = json.loads(r)
			# ~ partner.commercial_partner_id.ref = r["Customer"]["CustomerNumber"] 
			_logger.warn('%s Haze ref ref ' % partner.commercial_partner_id.ref)
			# ~ partner.commercial_partner_id.ref = int(r["Customer"]["CustomerNumber"])
			# ~ raise Warning(str(r))
			# ~ partner.commercial_partner_id.ref = r["Customer"]["CustomerNumber"]
			# ~ _logger.warn('%s Haze ref' % partner.commercial_partner_id.ref)
			# ~ _logger.warn('%s Haze ref' % partner.commercial_partner_id.ref)
			
			# ~ raise Warning(partner.commercial_partner_id.ref)
			return requests.get(url).json()  
			
	
