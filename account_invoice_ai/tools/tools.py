import logging
import requests
from langchain.tools import tool
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from typing_extensions import Annotated, TypedDict, Sequence, Any, List, Dict
from odoo.addons.ai_agent.models.ai_quest import AgentState
from langchain_core.tools import InjectedToolArg
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
import operator

from odoo import models, fields, api, _
from odoo.addons.ai_agent.models.ai_quest_session import AIQuestSession
# from odoo.addons.ai_agent.models.ai_quest import AgentState as State
from odoo.exceptions import UserError, ValidationError, Warning
# from odoo.tools.mail import html2plaintext
# from odoo.tools.safe_eval import safe_eval
from langgraph.graph.message import add_messages

_logger = logging.getLogger(__name__)

tool_state = {}


class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


@tool("mail_rfc822", return_direct=False)
def mail_rfc822(mail: str) -> dict:
    """Returns a dict with mail-format."""

    results = list(DDGS().text(query, max_results=5))

    return results if results else "No results found."


@tool("partner_search", return_direct=False)
def partner_search(email: str) -> int:
    """Searh partner using email."""

    partner = self.env['res.partner'].search([('mail', '=', email)], limit=1)
    return partner.id if partner else None


@tool("invoice_search", return_direct=False)
def invoice_search(number: str) -> int:
    """Searh invoice using number."""

    invoice = self.env['accout.move'].search([('number', '=', number)], limit=1)
    return invoice.id if invoice else None


def create_attachment_tool(state):
    @tool("process_attachments", return_direct=False)
    def process_attachments(query: str) -> str:
        """This gets data/string from a attachment :)"""
        print("Access to state in process_attachments: ", state.get('messages')[0].attachments)
        return f"It works!!!"
    return process_attachments
