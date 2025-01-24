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

import io
import re

from datetime import datetime
from hashlib import md5
from logging import getLogger
from zlib import compress, decompress
from PIL import Image, PdfImagePlugin

_logger = logging.getLogger(__name__)

tool_state = {}


class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


def mail_rfc822(state):

    @tool("mail_rfc822_tool", return_direct=False)
    def mail_rfc822_tool(mail_body: str) -> str:
        """Returns a json with values from eml file"""
        
        import json, base64, io, eml_parser, datetime, email

        attachment_ids = []

        if state.get("attachments"):
            attachment_ids = state["attachments"]
        elif state.get("session") and len(state["session"].message_ids.attachment_ids) != 0:
            attachment_ids = state["session"].message_ids.attachment_ids
        else:
            _logger.error(f"No attachments on email or given to agent")

        raw_attachments = []
        result = []

        if type([b"0"]) != type(attachment_ids):

            eml_files = list(filter(lambda attachment_id: ".eml" in attachment_id.name, attachment_ids))
            for eml_file in eml_files:
                raw_attachments.append(base64.b64decode(eml_file.datas))
       
        else:
            raw_attachments = attachment_ids

        def json_serial(obj):
            if isinstance(obj, datetime.datetime):
                serial = obj.isoformat()
                return serial

        for raw_attachment in raw_attachments:
            ep = eml_parser.EmlParser()
            parsed_eml = ep.decode_email_bytes(raw_attachment)
            test = email.message(raw_attachment)
            result.append(json.dumps(parsed_eml, default=json_serial))

        return result if len(result) != 0 else "No eml files to analyze"

    return mail_rfc822_tool


def partner_search(state):

    @tool("partner_search_tool", return_direct=False)
    def partner_search_tool(email: str) -> int:
        """Search partner using email."""

        state["mail"]

        partner = self.env['res.partner'].search([('mail', '=', email)], limit=1)
        return partner.id if partner else None

    return partner_search_tool

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
        attachments = state.get('messages')[0].attachments
        pdf_content = attachments.get_pdf_content()
        return pdf_content

    return process_attachments
