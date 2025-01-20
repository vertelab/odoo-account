import logging
import requests
from langchain.tools import tool
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

_logger = logging.getLogger(__name__)

@tool("mail_rfc822", return_direct=False)
def mail_rfc822(mail: str) -> dict:
    """Returns a dict with mail-format."""
    
    results = list(DDGS().text(query, max_results=5))

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

    
@tool("process_content", return_direct=False)
def process_content(url: str) -> str:   
    """Processes content from a webpage."""

    from bs4 import BeautifulSoup
    import requests

    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    return soup.get_text()

    # ~ <record id="account_invoice_ai_pdf" model="ai.tool">
      # ~ <field name="name">PDF-scrape</field>
      # ~ <field name="tool">pdf_scrape</field>
      # ~ <field name="tool_lib">odoo.addons.ai_agent.tools.pdf_scrape</field>
      # ~ <field name="image_128"></field>
    # ~ </record>
    # ~ <record id="account_invoice_ai_ocr" model="ai.tool">
      # ~ <field name="name">OCR-scrape</field>
      # ~ <field name="tool">ocr_scrape</field>
      # ~ <field name="tool_lib">odoo.addons.ai_agent.tools.ocr_scrape</field>
      # ~ <field name="image_128"></field>
    # ~ </record>
