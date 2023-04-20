from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def split_invoice_by_attachments(self):
        attachments = self.env['ir.attachment'].search([('res_model', '=', 'account.move'), ('res_id', '=', self.id)])
        if attachments:
            for file in attachments:
                new_invoice = self.copy()
                file.res_id = new_invoice.id
            self.unlink()
