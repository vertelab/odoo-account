from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ESRSLine(models.Model):
    _name = 'esrs.line'
    _description = ''

    name = fields.Char(compute="_compute_name", store=True)
    account_move_id = fields.Many2one(comodel_name="account.move")
    survey_id = fields.Many2one(comodel_name="survey.survey")
    document_csrd_id = fields.Many2one(comodel_name="document.csrd" )
    parent_document_csrd_id = fields.Many2one(comodel_name="document.csrd", related="document_csrd_id.parent_id", readonly=True, store=True)
    uom_id = fields.Many2one(comodel_name="uom.uom", required=True)
    data_value = fields.Float(string="Quantity", required=True)
    data_type = fields.Selection([('water','Vatten'), ('energy','Energi'), ('co2','CO2')])
    
    @api.depends("document_csrd_id", "uom_id", "survey_id", "account_move_id", "account_move_id.name", "account_move_id.state")
    def _compute_name(self):
        for record in self:
            record.name = record.document_csrd_id.csrd_name if record.document_csrd_id else ""
            record.name = f"{record.name} ({record.uom_id.name})" if record.uom_id.name else record.name
            record.name = f"{record.name} ({record.account_move_id.name})" if record.account_move_id.name else record.name
            record.name = f"{record.name} ({record.survey_id.display_name})" if record.survey_id.display_name else record.name

    # def write(self,vals):

    #     _logger.error(f"{vals=}")
        
    #     for record in self:
    #         esrs_line_ids = self.env['esrs.line'].search([("document_csrd_id", '=', record.document_csrd_id.id),("uom_id", "!=", vals.get('uom_id'))])
    #         if len(esrs_line_ids) > 1:
    #             raise UserError(_("A data point has a different UOM (Units of Measure) set. Please have the same UOM for all lines that use the same data point."))

    #     return super(ESRSLine,self).write(vals)

    # @api.model_create_multi
    # def create(self, vals_list):

    #     _logger.error(f"{vals_list=}")

    #     for record in vals_list:
    #         for filterd_records in filter(lambda val_rec: val_rec["document_csrd_id"] == record["document_csrd_id"], vals_list):
    #             if record["uom_id"] != filterd_records["uom_id"]:
    #                 raise UserError(_("A data point has a different UOM (Units of Measure) set. Please have the same UOM for all lines that use the same data point."))

    #     return super(ESRSLine, self).create(vals_list)


    @api.onchange("document_csrd_id")
    def set_uom_id(self):
        for record in self:
            esrs_line_ids = self.env['esrs.line'].search([("document_csrd_id", '=', record.document_csrd_id.id)])
            if len(esrs_line_ids) == 1:
                record.uom_id = esrs_line_ids.uom_id
            





