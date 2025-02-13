import json
import re
from typing import List, Dict, Any
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError
from langchain_core.messages import AIMessage

import logging

_logger = logging.getLogger(__name__)


class AIQuestSession(models.Model):
    _inherit = "ai.quest.session"

    move_id = fields.Many2one('account.move')
    ai_type = fields.Selection(selection_add=[('account-invoice', 'Invoice')], ondelete={'account-invoice': 'cascade'})

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


class AIQuest(models.Model):
    _inherit = "ai.quest"

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    ai_type = fields.Selection(selection_add=[('account-invoice', 'Invoice')], ondelete={'account-invoice': 'cascade'})

    def _serialize_ai_messages(self, ai_messages):
        filtered_messages = [msg for msg in ai_messages if msg.content.strip()]
        ai_invoice_data = []
        for ai_message in filtered_messages:
            if ai_message.content:
                json_data = self.json2dict(ai_message.content)
                if json_data:
                    ai_invoice_data.append(json_data)
        return ai_invoice_data

    def mail(self, mail, session):
        session.create_minimal_invoice()
        return super(AIQuest, self).mail(mail, session)

    def parse_invoice_data(self, res):
        ai_messages = [m for m in res.get('messages') if isinstance(m, AIMessage)]
        try:
            ai_invoice_data = self._serialize_ai_messages(ai_messages)[-1]
            invoice_data = ai_invoice_data.get('invoice')
            return invoice_data
        except IndexError:
            raise UserError("Error get the content from AI. Run this again.")

    def _get_or_create_partner(self, name):
        partner_id = self.env['res.partner'].search([('name', '=', name)], limit=1)
        if not partner_id:
            partner_id = self.env['res.partner'].create({
                'name': name,
                'company_type': 'company'
            })
        return partner_id.id

    def _get_currency(self, currency):
        currency_id = self.env['res.currency'].search([('name', '=', currency)], limit=1)
        if not currency_id:
            currency_id = self.env['res.currency'].search([('symbol', '=', currency)], limit=1)
        return currency_id.id

    def _create_vendor_bill(self, res, session):
        invoice_data = self.parse_invoice_data(res)
        customer_name = invoice_data.pop('customer', False)
        vendor_in_eu = invoice_data.pop('vendor_in_eu', False)
        customer_in_eu = invoice_data.pop('customer_in_eu', False)
        period_id = self.env['account.period'].date2period(invoice_data.get('date', fields.Date.today())).id
        invoice_data['partner_id'] = self._get_or_create_partner(invoice_data.pop('vendor', False))
        invoice_data['currency_id'] = self._get_currency(invoice_data.pop('currency', False))
        invoice_data['period_id'] = period_id
        invoice_data['invoice_date'] = invoice_data.get('date')
        invoice_data['move_type'] = 'in_invoice'
        invoice_data['invoice_line_ids'] = self._invoice_lines(invoice_data.pop('invoice_line_ids'))

        if session.move_id:
            session.move_id.write(invoice_data)
        else:
            self.env['account.move'].create(invoice_data)

    def _invoice_lines(self, invoice_lines):
        default_journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        default_account = default_journal.default_account_id.id
        default_tax = self.company_id.account_purchase_tax_id.ids
        lines = []
        for line in invoice_lines:
            if account_id := line.get('account_id'):
                dynamic_account_id = self.env['account.account'].search([
                    ('code', '=', account_id), ('company_id', '=', self.company_id.id)
                ], limit=1)
                if dynamic_account_id:
                    line['account_id'] = dynamic_account_id.id
                else:
                    line['account_id'] = default_account
            else:
                line['account_id'] = default_account

            if tax := line.pop('tax/vat', False):
                dynamic_tax_id = self.env['account.tax'].search([('name', '=', tax)])
                if dynamic_tax_id:
                    line['tax_ids'] = [(6, 0, dynamic_tax_id.ids)]
                else:
                    line['tax_ids'] = [(6, 0, default_tax)]
            else:
                line['tax_ids'] = [(6, 0, default_tax)]
            lines.append((0, 0, line))
        return lines
