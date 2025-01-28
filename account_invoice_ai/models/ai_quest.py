from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError
import json

import logging

_logger = logging.getLogger(__name__)


class AIQuest(models.Model):
    _inherit = "ai.quest"

    ai_type = fields.Selection(selection_add=[('account-invoice', 'Invoice')], ondelete={'account-invoice': 'cascade'})
    
    def _get_tools(self):
        super(AIQuest, self)._get_tools()

        @tool("mail_rfc822", return_direct=False)
        def mail_rfc822(mail: str) -> dict:
            """Returns a dict with mail-format."""
            
            results = list(DDGS().text(mail, max_results=5))

            return results if results else "No results found."

        @tool("partner_search", return_direct=False)
        def partner_search(email: str) -> int:   
            """Searh partner using email."""

            partner = self.env['res.partner'].search([('mail','=',email)],limit=1)
            return partner.id if partner else None

        @tool("invoice_search", return_direct=False)
        def invoice_search(number: str) -> int:   
            """Searh invoice using number."""

            invoice = self.env['accout.move'].search([('number','=',number)],limit=1)
            return invoice.id if invoice else None

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
                    },
                    {
                        "product_id": false,
                        "name": "Product B",
                        "account_id": 4000,
                        "quantity": 5,
                        "price_unit": 20.00,
                        "tax_ids": false
                    },
                    {
                        "product_id": false,
                        "name": "Product C",
                        "account_id": 4000,
                        "quantity": 8,
                        "price_unit": 10.00,
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