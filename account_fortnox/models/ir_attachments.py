# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _ 
from odoo.exceptions import UserError

import requests
import json
import time
import base64
import logging

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    fortnox_file_ref = fields.Char(string='Fortnox File ID', index=True, company_dependent=True)
    fortnox_file_archive_id = fields.Char(string='Fortnox File ArchiveID', index=True, company_dependent=True)
    fortnox_file_path = fields.Char(string='Fortnox File Path', index=True, company_dependent=True)
    fortnox_file_url = fields.Char(string='Fortnox File Url', index=True, company_dependent=True)
        
    def _upload_file_to_fortnox(self, company_id):           
        for file in self:
            if not file.fortnox_file_ref:
                url = "https://api.fortnox.se/3/inbox/?path=inbox_kf"
                file_content = base64.b64decode(file.datas)
                files = {
                    'file': (file.name, file_content, file.mimetype)
                }
                
                r = company_id.fortnox_request(
                    'post',
                    url,
                    files=files
                )
                _logger.warning(f"{r=}")
                if r.get("ErrorInformation", {}):
                    raise UserError(f"File upload went wrong {r}")
                file.fortnox_file_ref = r.get('File').get('Id')
                file.fortnox_file_archive_id = r.get('File').get('ArchiveFileId')
                file.fortnox_file_path = r.get('File').get('Path')
                file.fortnox_file_url = r.get('File').get('@url')
                   

