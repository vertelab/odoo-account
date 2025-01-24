from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError
from langchain_core.messages import AIMessage
import json

import logging

_logger = logging.getLogger(__name__)


class AIQuest(models.Model):
    _inherit = "ai.quest"

    ai_type = fields.Selection(selection_add=[('account-invoice', 'Invoice')], ondelete={'account-invoice': 'cascade'})

    def parse_invoice_data(self, res):
        print("parse_invoice_data", res)
        ai_messages = [m for m in res.get('messages') if isinstance(m, AIMessage)]
        print("ai_messages", ai_messages)
        print("ai_messages", ai_messages[-1])
        print("ai_messages", ai_messages[-1].content)
        extracted_dicts = self.json2dict(ai_messages[-1].content)
        invoice_data = extracted_dicts.get('invoice')
        return invoice_data

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

    def _create_vendor_bill(self, res):
        print("=============, _create_vendor_bill")

        invoice_data = self.parse_invoice_data(res)
        # vendor_name = invoice_data.pop('vendor')
        customer_name = invoice_data.pop('customer', False)
        vendor_in_eu = invoice_data.pop('vendor_in_eu', False)
        customer_in_eu = invoice_data.pop('customer_in_eu', False)
        invoice_data['partner_id'] = self._get_or_create_partner(invoice_data.pop('vendor', False))
        invoice_data['currency_id'] = self._get_currency(invoice_data.pop('currency', False))
        invoice_data['move_type'] = 'in_invoice'
        invoice_data['invoice_line_ids'] = self._invoice_lines(invoice_data.pop('invoice_line_ids'))

        self.env['account.move'].create(invoice_data)

    def _invoice_lines(self, invoice_lines):
        lines = []
        for line in invoice_lines:
            # Find matching account
            account_id = line.get('account_id', False)
            if account_id:
                account_id = self.env['account.account'].search([('code', '=', str(line.get('account_id')))], limit=1)
                if account_id:
                    line['account_id'] = account_id.id

            if not account_id:
                line['account_id'] = 26

            # Find and format tax information
            if tax := line.pop('tax/vat', False):
                tax_id = self.env['account.tax'].search([('name', 'ilike', tax)], limit=1)
                if tax_id:
                    line['tax_ids'] = [(6, 0, tax_id.ids)]

            lines.append((0, 0, line))

            _logger.warning(f"{line=}")
        return lines

    def test_create_invoice(self):
        json_test = """json { 
            "invoice": {
                "partner_id": 3,
                "invoice_date_due": "2023-12-31",
                "date": "2023-11-01",
                "ref": "INV-2023-001",
                "currency_id": 1,
                "fiscal_position_id": false,
                "move_type": "in_invoice",
                "invoice_line_ids": [
                    {
                        "product_id": false,
                        "name": "Product A",
                        "account_id": 4000,
                        "quantity": 10,
                        "price_unit": 15.00,
                        "tax_ids": false
                    }
                ]
            }
        }"""

        formatted_json = self.extract_and_parse_json(json_test)
        if not formatted_json:
            raise ValueError("Failed to parse JSON input")

        _logger.warning(f"{formatted_json=}")

        # Extract and create invoice
        invoice_data = formatted_json['invoice']
        invoice_lines = invoice_data.pop('invoice_line_ids')
        _logger.warning(f"{invoice_lines=}")
        _logger.warning(f"{invoice_data=}")

        invoice = self.env['account.move'].create(invoice_data)

        # Create invoice lines
        for line in invoice_lines:
            # Find matching account
            if line.get('account_id'):
                account_id = self.env['account.account'].search(
                    [('code', '=', str(line.get('account_id')))], limit=1
                )
                if account_id:
                    line['account_id'] = account_id.id

            # Find and format tax information
            if line.get('tax_ids'):
                tax_id = self.env['account.tax'].search(
                    [('name', 'ilike', line.get('tax_ids'))], limit=1
                )
                if tax_id:
                    line['tax_ids'] = [(6, 0, tax_id.ids)]

            line['move_id'] = invoice.id
            _logger.warning(f"{line=}")

            line_id = self.env['account.move.line'].create(line)
            _logger.warning(f"{line_id=}")

    def extract_and_parse_json(self, llm_output):
        """
        Extract and parse JSON from input string, handling potential 'json' prefix.

        Args:
            llm_output (str): Input string containing JSON, possibly with 'json' prefix

        Returns:
            dict: Parsed JSON object or None if parsing fails
        """
        # Clean up the input string
        json_str = llm_output.strip()
        if json_str.startswith('json'):
            json_str = json_str[4:].strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            _logger.error(f"JSON parsing error: {e}")
            # If direct parsing fails, try to find proper JSON boundaries
            json_start = json_str.find('{')
            if json_start == -1:
                return None

            json_str = json_str[json_start:]
            bracket_count = 0

            for i, char in enumerate(json_str):
                if char == '{':
                    bracket_count += 1
                elif char == '}':
                    bracket_count -= 1

                if bracket_count == 0:
                    # Found matching end bracket
                    json_str = json_str[:i + 1]
                    try:
                        # Convert JavaScript 'false' to Python 'False'
                        json_str = json_str.replace('false', 'false')
                        return json.loads(json_str)
                    except json.JSONDecodeError as e:
                        _logger.error(f"Final JSON parsing error: {e}")
                        return None

            return None


class AIQuestSession(models.Model):
    _inherit = 'ai.quest.session'

    ai_type = fields.Selection(selection_add=[('account-invoice', 'Invoice')], ondelete={'account-invoice': 'cascade'})
