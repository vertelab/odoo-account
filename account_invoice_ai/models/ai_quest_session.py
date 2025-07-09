import json
import logging
import re
import eml_parser
import base64
from typing import List, Dict, Any

from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError

_logger = logging.getLogger(__name__)


class AIQuestSession(models.Model):
    _inherit = "ai.quest.session"
    invoice_metadata = fields.Text(string="Invoice Metadata", readonly=True)


