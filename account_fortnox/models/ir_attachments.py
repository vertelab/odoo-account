# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _ 
from odoo.exceptions import Warning,UserError

import requests
import json
import time
import base64
import logging

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    fortnox_ref = fields.Char(string='Fortnox File ID', index=True, company_dependent=True)
    fortnox_ArchiveFileId = fields.Char(string='Fortnox File ArchiveID', index=True, company_dependent=True)
    fortnox_Path = fields.Char(string='Fortnox File Path', index=True, company_dependent=True)
    fortnox_Url = fields.Char(string='Fortnox File Url', index=True, company_dependent=True) 
    def file_upload(self, company_id = None):
        if not company_id:
           company_id = self.env.user.company_id
        for file in self:
            if not file.fortnox_ref:
                url = "https://api.fortnox.se/3/inbox/?path=inbox_kf"
                file_content = base64.b64decode(file.datas)
                files = {
                'file': (file.name, file_content, file.mimetype)
                }
                _logger.warning(f"{files=}")
                r = company_id.fortnox_request(
                    'post',
                    url,
                    files=files
                )
                if r.get("ErrorInformation", {}):
                    raise UserError(f"File upload went wrong {r}")
                if r.get('File'):
                   file.fortnox_ref = r.get('File').get('Id')
                   file.fortnox_ArchiveFileId = r.get('File').get('ArchiveFileId')
                   file.fortnox_Path = r.get('File').get('Path')
                   file.fortnox_Url = r.get('File').get('@url')
                   

