import logging
import requests
from langchain.tools import tool
from typing_extensions import Annotated, TypedDict, Dict
from odoo.addons.ai_agent.models.ai_quest import AgentState
from pydantic import BaseModel, Field

from odoo.addons.ai_agent.models.ai_quest_session import AIQuestSession
from langgraph.graph.message import add_messages

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
        
        import json, base64, datetime, eml_parser

        attachment_ids = []

        if state.get("attachments"):
            attachment_ids = state["attachments"]
        elif state.get("session") and len(state["session"].message_ids.attachment_ids) != 0:
            attachment_ids = state["session"].message_ids.attachment_ids
        else:
            _logger.error(f"No attachments on email or given to agent")

        raw_attachments = []
        result = {}
        counter = 0

        if type([b"0"]) != type(attachment_ids):

            eml_files = list(filter(lambda attachment_id: ".eml" in attachment_id.name, attachment_ids))
            for eml_file in eml_files:
                raw_attachments.append(eml_file.datas)
       
        else:
            raw_attachments = attachment_ids

        def json_serial(obj):
            if isinstance(obj, datetime.datetime):
                serial = obj.isoformat()
                return serial

        for raw_attachment in raw_attachments:
            counter += 1
            ep = eml_parser.EmlParser()
            raw_attachment = base64.b64decode(raw_attachment)
            parsed_eml = ep.decode_email_bytes(raw_attachment)
            result.update({f"email_{counter}": json.dumps(parsed_eml, default=json_serial)})

        return json.dumps(result) if len(result) != 0 else "No eml files to analyze"

    return mail_rfc822_tool


def partner_search(state):
    @tool("partner_search_tool", return_direct=False)
    def partner_search_tool(email: str) -> str:
        """Search partner using email and returns an id"""

        if state.get("session"):
            partner = state["session"].env['res.partner'].search([('email', '=', email)], limit=1)
            return str(partner.id) if partner else "No partner with that email found"

        return "failed no session in state"

    return partner_search_tool


@tool("invoice_search", return_direct=False)
def invoice_search(number: str) -> int:
    """Searh invoice using number."""

    invoice = self.env['accout.move'].search([('number', '=', number)], limit=1)
    return invoice.id if invoice else None


def create_attachment_tool(state):
    @tool("process_attachments", return_direct=False)
    def process_attachments(query: str) -> str:
        """This gets data/string from an attachment :)"""
        session = state.get('session')
        session_pdf_attachment = session.env['ir.attachment'].search([
            ('res_model', '=', 'ai.quest.session'),
            ('res_id', '=', session.id),
            ('mimetype', '=', 'application/pdf'),
        ], limit=1)
        print("pdf_attachment", session_pdf_attachment)
        # if state.get('messages')[0].attachments:
        #     attachment = state.get('messages')[0].attachments[-1]
        #     pdf_content = attachment.get_pdf_content()
        #     return pdf_content

        if session_pdf_attachment:
            pdf_content = session_pdf_attachment.get_pdf_content()
            return pdf_content

    return process_attachments
