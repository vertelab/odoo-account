from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _description = ''
    _inherit = 'account.move'

    esrs_line_ids = fields.One2many(comodel_name="esrs.line", inverse_name="account_move_id")