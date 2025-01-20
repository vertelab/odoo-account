from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class AIQuestSession(models.Model):
    _inherit = 'ai.quest.session'

    ai_type = fields.Selection(selection_add=[('account-invoice', 'Invoice')], ondelete={'account-invoice': 'cascade'})

class AIAgent(models.Model):
    _inherit = "ai.agent"

    ai_type = fields.Selection(selection_add=[('account-invoice', 'Invoice')], ondelete={'account-invoice': 'cascade'})

class AIQuest(models.Model):
    _inherit = "ai.quest"

    ai_type = fields.Selection(selection_add=[('account-invoice', 'Invoice')], ondelete={'account-invoice': 'cascade'})

class AccountMove(models.Model):
    _inherit = "account.move"

    ai_session_id = fields.Many2one(comodel_name='ai.quest.session',string="",help="")

