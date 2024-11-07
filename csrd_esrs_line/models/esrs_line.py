from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)

class ESRSLine(models.Model):
    _name = 'esrs.line'
    _description = ''

    name = fields.Char(compute="compute_name", store=True)
    account_move_id = fields.Many2one(comodel_name="account.move")
    document_csrd_id = fields.Many2one(comodel_name="document.csrd" )
    uom_id = fields.Many2one(comodel_name="uom.uom")
    # date = fields.Datetime()
    quantity = fields.Float()

    @api.depends("document_csrd_id", "uom_id")
    def compute_name(self):
        for record in self:
            record.name = record.document_csrd_id.csrd_name if record.document_csrd_id else ""
            record.name = f"{record.name} ({record.uom_id.name})" if record.uom_id.name else record.name

    @api.onchange("document_csrd_id")
    def set_quantity_and_uom(self):
        for record in self:

            if record.document_csrd_id:

                if record.document_csrd_id.implementation_numerical:
                    record.quantity = record.document_csrd_id.implementation_numerical
                
                if record.document_csrd_id.uom_id:
                    record.uom_id = record.document_csrd_id.uom_id




