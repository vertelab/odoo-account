from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)

class DocumentCSRD(models.Model):
    _description = ''
    _inherit = 'document.csrd'

    uom_id = fields.Many2one(comodel_name="uom.uom")

    esrs_line_ids = fields.One2many(comodel_name="esrs.line", inverse_name="document_csrd_id")

    data_value = fields.Float(string="Data Value", compute="_compute_data_value")

    parent_id = fields.Many2one(comodel_name="document.csrd")

    child_ids = fields.One2many(comodel_name="document.csrd",inverse_name="parent_id") 

    count_esrs_lines = fields.Integer(compute="_compute_count_esrs_lines")

    # @api.model
    # def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
    #     """ Override search() to always show inactive children when searching via ``child_of`` operator. The ORM will
    #     always call search() with a simple domain of the form [('parent_id', 'in', [ids])]. """
    #     # a special ``domain`` is set on the ``child_ids`` o2m to bypass this logic, as it uses similar domain expressions
    #     if len(args) == 1 and len(args[0]) == 3 and args[0][:2] == ('parent_id','in') \
    #             and args[0][2] != [False]:
    #         self = self.with_context(active_test=False)
    #     return super(Partner, self)._search(args, offset=offset, limit=limit, order=order,
    #                                         count=count, access_rights_uid=access_rights_uid)

    @api.depends("esrs_line_ids")
    def _compute_count_esrs_lines(self):
        for record in self:
            record.count_esrs_lines = len(record.esrs_line_ids)

    def get_children(self):
        self.ensure_one()
        action = {
            'name': 'ESRS_lines',
            'type': 'ir.actions.act_window',
            'res_model': 'esrs.line',
            'view_mode': 'tree',
            'target': 'current',
            'domain': [('id', 'in', self.esrs_line_ids.ids)]
        }
        return action

    def open_survey_wizard(self):
        self.ensure_one()
        if self.survey_id:
            return {
                'name': "Test Wizard",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'document.csrd.gather.survey.wizard',
                'context': {'default_survey_id': self.survey_id.id, 'default_document_csrd_id': self.id},
                'target': 'new',
            }

    def _compute_data_value(self):
        for record in self:
            record.data_value = sum(map(lambda esrs_line_id: esrs_line_id.data_value, record.esrs_line_ids))

    def _compute_uom_id(self):
        for record in self:
            record.uom_id = record

    @api.onchange("parent_id")
    def set_category_on_childe(self):
        for record in self:
            record.category_id = record.parent_id.category_id
