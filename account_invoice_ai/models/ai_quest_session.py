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
    move_id = fields.Many2one('account.move')
    ai_type = fields.Selection(selection_add=[('account-invoice', 'Invoice')], ondelete={'account-invoice': 'cascade'})

    def action_view_move(self):
        view = self.env.ref('account.view_move_form')
        return {
            'name': _('Account Move'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_id': self.move_id.id
        }

    def create_minimal_invoice(self):
        if self.ai_quest_id.ai_type == 'account-invoice':
            period_id = self.env['account.period'].search([
                ('state', '=', 'draft'), ('company_id', '=', self.company_id.id)
            ], limit=1, order="date_stop")
            self.move_id = self.env['account.move'].create({
                'move_type': "in_invoice",
                'period_id': period_id.id,
                'ai_session_id': self.id
            })

            if self.move_id:
                attachments = self.env['ir.attachment'].search([
                    ('res_model', '=', self._name), ('res_id', '=', self.id)
                ])
                for attachment in attachments:
                    self.env['ir.attachment'].create({
                        'name': attachment.name,
                        'type': attachment.type,
                        'datas': attachment.datas,
                        'res_model': 'account.move',
                        'res_id': self.move_id.id,
                    })
