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
            period_id = self.env['account.period'].search([('state', '=', 'draft')], limit=1, order="date_stop")
            self.move_id = self.env['account.move'].create({
                'move_type': "in_invoice",
                'period_id': period_id.id,
                'ai_session_id': self.id
            })

            if self.move_id:
                attachments = self.env['ir.attachment'].search(
                    [('res_model', '=', self._name), ('res_id', '=', self.id)])
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
    latest_session_id = fields.Many2one('ai.quest.session', string="Latest Session")

    def mail(self, mail, session):
        session.create_minimal_invoice()
        if session.move_id:
            self.latest_session_id = session.id

        return super(AIQuest, self).mail(mail, session)

    def parse_invoice_data(self, res):
        ai_messages = [m for m in res.get('messages') if isinstance(m, AIMessage)]
        # print("ai_messages", ai_messages)
        try:
            extracted_dicts = self.json2dict(ai_messages[-1].content)
            invoice_data = extracted_dicts.get('invoice')
            return invoice_data
        except IndexError:
            raise UserError("Error get the content from AI. Run this again.")

    def _get_or_create_partner(self, name):
        partner_id = self.env['res.partner'].search([('name', '=', name)], limit=1)
        if not partner_id:
            partner_id = self.env['res.partner'].create({'name': name})
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
        _logger.warning(f"period_id period_id {period_id=}")
        _logger.warning(f"1{invoice_data['date']=}")
        invoice_data['partner_id'] = self._get_or_create_partner(invoice_data.pop('vendor', False))
        invoice_data['currency_id'] = self._get_currency(invoice_data.pop('currency', False))
        invoice_data['period_id'] = period_id
        invoice_data['invoice_date'] = invoice_data.get('date')
        invoice_data['move_type'] = 'in_invoice'
        invoice_data['invoice_line_ids'] = self._invoice_lines(invoice_data.pop('invoice_line_ids'))
        print(f"invoice_data {invoice_data}")

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
            line['account_id'] = default_account
            line['tax_ids'] = [(6, 0, default_tax)]
            line.pop("tax/vat", False)
            lines.append((0, 0, line))

            _logger.warning(f"{line=}")
        return lines
