from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)

class DocumentCSRDGatherSurveyWizard(models.TransientModel):
    _name = 'document.csrd.gather.survey.wizard'
    _description = 'scaffold_test.scaffold_test'

    name = fields.Char()
    survey_id = fields.Many2one(comodel_name="survey.survey", required=True)
    survey_question_id = fields.Many2one(comodel_name="survey.question", required=True)
    survey_question_suggested_answer_id = fields.Many2one(comodel_name="survey.question.answer")
    document_csrd_id = fields.Many2one(comodel_name="document.csrd", required=True)
    is_one_answer = fields.Boolean(string="Singel Answer",help="If true, you can store the result of the number of a specified answer on the main data point.")

    def gather_survey_data(self):
        
        
        #uom_id = self.env["uom.uom"].search([("name", "=", "Units")])
        uom_id = self.env.ref('uom.product_uom_unit')

        count_answers = 0

        if self.is_one_answer:

            count_answers = self.env["survey.user_input.line"].search_count([("question_id", "=", self.survey_question_id.id),("suggested_answer_id", "=", self.survey_question_suggested_answer_id.id)])
            
            _logger.error(f"{count_answers=}")

            self.env["esrs.line"].create({'document_csrd_id': self.document_csrd_id.id, 'survey_id': self.survey_id.id, 'uom_id': uom_id.id, 'data_value': count_answers})
            
        else:
        
            for suggested_answer_id in self.survey_question_id.suggested_answer_ids:

                count_answers = self.env["survey.user_input.line"].search_count([("question_id", "=", self.survey_question_id.id),("suggested_answer_id", "=", suggested_answer_id.id)])

                _logger.error(f"{count_answers=}")

                new_document_csrd_id = self.env["document.csrd"].create({"csrd_name": f"{self.document_csrd_id.name} [{suggested_answer_id.value}]", "parent_id": self.document_csrd_id.id, "survey_id": self.survey_id.id})

                self.env["esrs.line"].create({'document_csrd_id': new_document_csrd_id.id, 'survey_id': self.survey_id.id, 'uom_id': uom_id.id, 'data_value': count_answers})

        return  {'type': 'ir.actions.act_window_close'}

        

