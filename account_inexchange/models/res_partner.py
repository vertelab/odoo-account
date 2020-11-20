# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# ~ from odoo import api, fields, models
# ~ from odoo.exceptions import Warning

# ~ import requests
# ~ import json

# ~ import logging
# ~ _logger = logging.getLogger(__name__)


# ~ class Partner(models.Model):
	# ~ _inherit = 'res.partner'
	
	# ~ def partner_create(self):
		# ~ # Company (POST /v1/api/companies/register/ HTTP/1.1)
		# ~ for partner in self:
			# ~ if not partner.commercial_partner_id.ref:
				# ~ try:
				# ~ url = "https://testapi.inexchange.se/api/companies/register/ HTTP/1.1"
				# ~ """ r = response """
				# ~ r = self.env['res.config.settings'].inexchange_request('POST', url,
					# ~ data={
					# ~ "erpId": partner.commercial_partner_id.id,
					# ~ "orgNo": partner.commercial_partner_id.company_registry,
					# ~ "vatNo": partner.commercial_partner_id.vat,
					# ~ "name": partner.commercial_partner_id.name,
					# ~ "erpProduct": "DEMO Product 1.0",
					# ~ "city": partner.city,
					# ~ "countryCode": "SE",
					# ~ "languageCode": "sv-SE",
					# ~ "email": partner.email,
					# ~ "isVatRegistered": true,
					# ~ "processes": [
						# ~ "SendInvoices",
						# ~ "ReceiveInvoices"
					# ~ ]})
			# ~ r = json.loads(r)
			# ~ partner.commercial_partner_id.ref = r["companyId"] 
			# ~ return r  
# ~ #FIXME:make inexchange_update auto-updating.

	# ~ @api.multi
	# ~ def partner_update(self):
		# ~ # Customer (PUT https://api.inexchange.se/3/customers)
		# ~ for partner in self:
			# ~ if partner.commercial_partner_id.ref:
				# ~ url = "https://testapi.inexchange.se/api/companies/register/ HTTP/1.1" % partner.commercial_partner_id.ref
				# ~ """ r = response """
				# ~ r = self.env['res.config.settings'].inexchange_request('POST', url,
					# ~ data = {
					# ~ "erpId": partner.commercial_partner_id.id,
					# ~ "orgNo": partner.commercial_partner_id.company_registry,
					# ~ "vatNo": partner.commercial_partner_id.vat,
					# ~ "name": partner.commercial_partner_id.name,
					# ~ "erpProduct": None,
					# ~ "city": partner.city,
					# ~ "countryCode": "SE",
					# ~ "languageCode": "sv-SE",
					# ~ "email": partner.email,
					# ~ "isVatRegistered": true,
					# ~ "processes": [
						# ~ "SendInvoices",
						# ~ "ReceiveInvoices"
					# ~ ]})
			# ~ r = json.loads(r)
			# ~ partner.commercial_partner_id.ref = r["Customer"]["CustomerNumber"] 
			# ~ _logger.warn('%s Haze ref ref ' % partner.commercial_partner_id.ref)
			# ~ return r  
			
	
