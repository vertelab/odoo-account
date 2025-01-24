from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError
import json

import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    ai_session_id = fields.Many2one(comodel_name='ai.quest.session', string="", help="")
