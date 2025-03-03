from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError
import json

import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    ai_session_id = fields.Many2one(comodel_name='ai.quest.session', string="", help="")

    def action_view_ai_session(self):
        view = self.env.ref('ai_agent.ai_quest_session_form')
        return {
            'name': _('AI Session'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ai.quest.session',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_id': self.ai_session_id.id
        }

