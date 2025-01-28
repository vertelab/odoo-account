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

    def create_minimal_invoice(self):
        if self.ai_quest_id.ai_type == 'account-invoice':
            period_id = self.env['account.period'].search([('state', '=', 'draft')], limit=1, order="date_stop")
            self.move_id = self.env['account.move'].create({
                'move_type': "in_invoice",
                'period_id': period_id.id,
                'ai_session_id': self.id
            })

            if self.move_id:
                attachments = self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', '=', self.id)])
                for attachment in attachments:
                    self.env['ir.attachment'].create({
                        'name': attachment.name,
                        'type': attachment.type,
                        'datas': attachment.datas,
                        'res_model': 'account.move',
                        'res_id': self.move_id.id,
                    })


    # def _message_set_main_attachment_id(self, attachment_ids):
    #     if self.ai_quest_id and self.message_ids[0].message_type == "email":
    #     thread_ids = super(AIQuestSession, self)._message_set_main_attachment_id(attachment_ids)
    #
    #     self.create_minimal_invoice()
    #     return thread_ids

    # def _message_set_main_attachment_id(self, attachment_ids):
    #     # thread_ids =
    #
    #     _logger.error(f"{self.session=}")
    #
    #     if self.ai_quest_id and self.message_ids[0].message_type == "email":
    #         self.create_minimal_invoice()
    #         _logger.warning(f"{self.message_ids[0].body=}")
    #
    #         self.ai_quest_id.mail(mail=self.message_ids[0], session=self)
    #
    #     return super(AIQuestSession, self)._message_set_main_attachment_id(attachment_ids)


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

    def _extract_json_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def has_json_object(content: str) -> bool:
            # Check if content contains JSON code block and invoice structure
            return '```json' in content and '"invoice"' in content

        # Filter messages that contain JSON objects
        json_messages = []

        for msg in messages:
            # Skip if message has no content
            if not msg.get('content'):
                continue

            if has_json_object(msg['content']):
                # Extract JSON content between ```json and ``` markers
                json_content = re.search(r'```json\s*(\{.*?\})\s*```', msg['content'], re.DOTALL)
                if json_content:
                    try:
                        # Parse the extracted JSON
                        parsed_json = json.loads(json_content.group(1))
                        json_messages.append({
                            'message_id': msg.get('id', ''),
                            'json_content': parsed_json
                        })
                    except json.JSONDecodeError:
                        print(f"Failed to parse JSON for message {msg.get('id', '')}")

        return json_messages

#     def mail_test_wizard(self):
#         ai_messages = [
#
# AIMessage(content='Please provide the text or image of the invoice so I can extract the important information from it.', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 21, 'prompt_tokens': 404, 'total_tokens': 425, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_name': 'gpt-4o-mini-2024-07-18', 'system_fingerprint': 'fp_bd83329f63', 'finish_reason': 'stop', 'logprobs': None}, id='run-d2915725-9137-4de4-8b48-6f1327a7f820-0', usage_metadata={'input_tokens': 404, 'output_tokens': 21, 'total_tokens': 425, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 0}}),
#
# AIMessage(content='Please provide the text or image of the invoice so I can extract the important information from it.', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 21, 'prompt_tokens': 404, 'total_tokens': 425, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_name': 'gpt-4o-mini-2024-07-18', 'system_fingerprint': 'fp_bd83329f63', 'finish_reason': 'stop', 'logprobs': None}, id='run-d2915725-9137-4de4-8b48-6f1327a7f820-0', usage_metadata={'input_tokens': 404, 'output_tokens': 21, 'total_tokens': 425, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 0}}),
#
# AIMessage(content='Please provide the text or image of the invoice so I can extract the important information from it.', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 21, 'prompt_tokens': 414, 'total_tokens': 435, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_name': 'gpt-4o-mini-2024-07-18', 'system_fingerprint': 'fp_bd83329f63', 'finish_reason': 'stop', 'logprobs': None}, id='run-ae62a309-0824-4310-acbc-5c55b751e01f-0', usage_metadata={'input_tokens': 414, 'output_tokens': 21, 'total_tokens': 435, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 0}}),
#
# AIMessage(content='Please provide the text or image of the invoice so I can extract the important information from it.', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 21, 'prompt_tokens': 414, 'total_tokens': 435, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_name': 'gpt-4o-mini-2024-07-18', 'system_fingerprint': 'fp_bd83329f63', 'finish_reason': 'stop', 'logprobs': None}, id='run-ae62a309-0824-4310-acbc-5c55b751e01f-0', usage_metadata={'input_tokens': 414, 'output_tokens': 21, 'total_tokens': 435, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 0}}),
#
#
# AIMessage(content='', additional_kwargs={'tool_calls': [{'id': 'call_9uPy1oASPAGudRBQTxlws766', 'function': {'arguments': '{"query":"invoice details"}', 'name': 'process_attachments'}, 'type': 'function'}], 'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 17, 'prompt_tokens': 414, 'total_tokens': 431, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_name': 'gpt-4o-mini-2024-07-18', 'system_fingerprint': 'fp_bd83329f63', 'finish_reason': 'tool_calls', 'logprobs': None}, id='run-e8b0e7ed-4f74-4611-95a8-9d4c2e314e39-0', tool_calls=[{'name': 'process_attachments', 'args': {'query': 'invoice details'}, 'id': 'call_9uPy1oASPAGudRBQTxlws766', 'type': 'tool_call'}], usage_metadata={'input_tokens': 414, 'output_tokens': 17, 'total_tokens': 431, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 0}}),
#
#
# AIMessage(content='Based on the extracted invoice details, here is the structured JSON object:\n\n```json\n{\n    "invoice": {\n        "customer": "SKF RECONDOLI AB",\n        "vendor": "St1 Sverige AB",\n        "invoice_date_due": "2025-01-15",\n        "date": "2024-12-31",\n        "ref": "8101754694",\n        "currency": "SEK",\n        "vendor_in_eu": "true",\n        "customer_in_eu": "true",\n        "invoice_line_ids": [\n            {\n                "name": "Diesel",\n                "quantity": 32,\n                "price_unit": 29.19,\n                "account_id": "",\n                "tax/vat": "25.00"\n            }\n        ]\n    }\n}\n```\n\n### Explanation of the fields:\n- **customer**: Name of the customer as per the invoice.\n- **vendor**: Name of the vendor who issued the invoice.\n- **invoice_date_due**: Due date for payment.\n- **date**: Invoice issuance date.\n- **ref**: Invoice number.\n- **currency**: Currency used in the transaction.\n- **vendor_in_eu**: Indicates if the vendor is within the European Union (true in this case).\n- **customer_in_eu**: Indicates if the customer is within the European Union (true in this case).\n- **invoice_line_ids**: Contains details about the products/services billed, including name, quantity, unit price, and applicable tax rate. \n\nFeel free to ask if you need further modifications or additional details!', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 333, 'prompt_tokens': 1501, 'total_tokens': 1834, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_name': 'gpt-4o-mini-2024-07-18', 'system_fingerprint': 'fp_bd83329f63', 'finish_reason': 'stop', 'logprobs': None}, id='run-dc77f5d7-6133-4049-8cd6-1206b0b618d4-0', usage_metadata={'input_tokens': 1501, 'output_tokens': 333, 'total_tokens': 1834, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 0}}),
#
# AIMessage(content='Based on the extracted invoice details, here is the structured JSON object:\n\n```json\n{\n    "invoice": {\n        "customer": "SKF RECONDOLI AB",\n        "vendor": "St1 Sverige AB",\n        "invoice_date_due": "2025-01-15",\n        "date": "2024-12-31",\n        "ref": "8101754694",\n        "currency": "SEK",\n        "vendor_in_eu": "true",\n        "customer_in_eu": "true",\n        "invoice_line_ids": [\n            {\n                "name": "Diesel",\n                "quantity": 32,\n                "price_unit": 29.19,\n                "account_id": "",\n                "tax/vat": "25.00"\n            }\n        ]\n    }\n}\n```\n\n### Explanation of the fields:\n- **customer**: Name of the customer as per the invoice.\n- **vendor**: Name of the vendor who issued the invoice.\n- **invoice_date_due**: Due date for payment.\n- **date**: Invoice issuance date.\n- **ref**: Invoice number.\n- **currency**: Currency used in the transaction.\n- **vendor_in_eu**: Indicates if the vendor is within the European Union (true in this case).\n- **customer_in_eu**: Indicates if the customer is within the European Union (true in this case).\n- **invoice_line_ids**: Contains details about the products/services billed, including name, quantity, unit price, and applicable tax rate. \n\nFeel free to ask if you need further modifications or additional details!', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 333, 'prompt_tokens': 1501, 'total_tokens': 1834, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_name': 'gpt-4o-mini-2024-07-18', 'system_fingerprint': 'fp_bd83329f63', 'finish_reason': 'stop', 'logprobs': None}, id='run-dc77f5d7-6133-4049-8cd6-1206b0b618d4-0', usage_metadata={'input_tokens': 1501, 'output_tokens': 333, 'total_tokens': 1834, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 0}}),
#
# AIMessage(content='To extract the important information from an incoming invoice, please provide the text or details of the invoice you would like me to process.', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 28, 'prompt_tokens': 726, 'total_tokens': 754, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_name': 'gpt-4o-mini-2024-07-18', 'system_fingerprint': 'fp_bd83329f63', 'finish_reason': 'stop', 'logprobs': None}, id='run-eb994103-295b-466b-82da-9ee0253ccb1d-0', usage_metadata={'input_tokens': 726, 'output_tokens': 28, 'total_tokens': 754, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 0}})
#
#
# ]

    def parse_invoice_data(self, res):
        ai_messages = [m for m in res.get('messages') if isinstance(m, AIMessage)]
        print("ai_messages", ai_messages)
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
        _logger.warning(f"{invoice_data=}")
        _logger.warning(f"1{invoice_data['date']=}")
        # vendor_name = invoice_data.pop('vendor')
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
