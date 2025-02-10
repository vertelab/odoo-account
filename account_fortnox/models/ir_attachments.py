# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _ 
from odoo.exceptions import Warning,UserError

import requests
import json
import time

import logging

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    fortnox_ref = fields.Char(string='Fortnox File ID', index=True, company_dependent=True)

    def file_upload(self, company_id = None):
        if not company_id:
           company_id = self.env.user.company_id
        for file in self:
            
            #raise UserError("test create")
            if not file.fortnox_ref:
                url = "https://api.fortnox.se/3/inbox"
                r = company_id.fortnox_request(
                    'post',
                    url,
                    data={
                    "File": {
                    "@url":f"{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}/{file.local_url}",
                    #"ArchiveFileId": "string",
                    #"Comments": "string",
                    "Id": file.checksum,
                    "Name": file.name,
                    "Path": "string",
                    "Size": 0
                    }
                    })
                if r.get("ErrorInformation", {}).get("code") in [2000357]:
                    raise UserError(f"File upload went wrong {r}")
                _logger.warning("CHECK HERE"*100)
                _logger.warning(f"{r=}")

    def connect_file_and_invoice(self, invoice):
        self.ensure_one()
        if not self.fortnox_ref:
            self.file_upload(company_id)

        url = "https://api.fortnox.se/3/inbox"
        r = company_id.fortnox_request(
            'post',
            url,
            data={
            "entityId": invoice.fortnox_ref,
            "entityType": "F",
            "fileId": self.fortnox_ref,
            "id": self.checksum,
            "includeOnSend": True
            })
        if r.get("ErrorInformation", {}).get("code") in [2000357]:
            raise UserError(f"File connection went wrong {r}")
        _logger.warning("CHECK HERE"*100)
        _logger.warning(f"{r=}")


    # def partner_update(self, company_id):
    #     for partner in self:
    #         VATType = partner.commercial_partner_id.property_account_position_id.fortnox_vat_type if partner.commercial_partner_id and partner.commercial_partner_id.property_account_position_id and partner.commercial_partner_id.property_account_position_id.fortnox_vat_type else "SEVAT"
    #         _logger.warning(
    #             f"UPDATING PARTNER {partner=} {partner.commercial_partner_id=} {partner.commercial_partner_id.fortnox_ref=} {VATType=}")
    #         if partner.commercial_partner_id.fortnox_ref:
    #             url = "https://api.fortnox.se/3/customers/%s" % partner.commercial_partner_id.fortnox_ref
    #             company_id.fortnox_request(
    #                 'put',
    #                 url,
    #                 data={
    #                     "Customer": {
    #                         "Address1": partner.street,
    #                         "City": partner.city,
    #                         "CountryCode": partner.country_id.code,
    #                         #"Currency": "SEK",
    #                         "Email": partner.email or None,
    #                         "Name": partner.commercial_partner_id.name,
    #                         "Phone1": partner.commercial_partner_id.phone,
    #                         "Phone2": None,
    #                         "PriceList": "A",
    #                         "ShowPriceVATIncluded": False,
    #                         "Type": "COMPANY",
    #                         "VATType": VATType,
    #                         "WWW": partner.commercial_partner_id.website,
    #                         "YourReference": partner.name,
    #                         "ZipCode": partner.zip,
    #                     }
    #                 })

    # def partner_get(self, company_id):
    #     for partner in self:
    #         url = "https://api.fortnox.se/3/customers/"
    #         """ r = response """
    #         company_id.fortnox_request(
    #             'get',
    #             url,
    #         )
