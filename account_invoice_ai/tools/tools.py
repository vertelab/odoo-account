import base64
import datetime
import eml_parser
import json
import logging

from langchain.tools import tool
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict, List

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
        """process mail eml file"""

        logging.info("calling mail_rfc822_tool")

        attachment_ids = []

        if state.get("attachments"):
            attachment_ids = state["attachments"]
        elif state.get("session") and len(state["session"].message_ids.attachment_ids) != 0:
            attachment_ids = state["session"].message_ids.attachment_ids
        else:
            _logger.error(f"No attachments on email or given to agent")
        result = False

        if not isinstance(attachment_ids, list):
            raw_attachments = attachment_ids.filtered(
                lambda attachment: attachment.mimetype == "message/rfc822"
            ).mapped("datas")
        else:
            raw_attachments = attachment_ids

        # for raw_attachment in raw_attachments:
        ep = eml_parser.EmlParser()
        if raw_attachments:
            raw_attachment = base64.b64decode(raw_attachments[0])
            parsed_eml = ep.decode_email_bytes(raw_attachment)
            # result.append(parsed_eml.get('header'))
            result = json.dumps(parsed_eml.get('header'))
            return result

        # result = "Email header not found, so no "
        return "Email header not found, so no "

    return mail_rfc822_tool


def partner_search(state):
    @tool("partner_search_tool", return_direct=False)
    def partner_search_tool(email: str) -> str:
        """Search partner using email and returns an id"""
        logging.info("calling partner_search_tool")

        if state.get("session"):
            partner = state["session"].env['res.partner'].search([('email', '=', email)], limit=1)
            if partner:
                return f"Partner ID: {partner.id} and name is {partner.name}"
            else:
                return "No partner with that email found"
        return "failed no session in state"

    return partner_search_tool


@tool("invoice_search", return_direct=False)
def invoice_search(number: str) -> int:
    """Search invoice using number."""

    invoice = self.env['account.move'].search([('number', '=', number)], limit=1)
    return invoice.id if invoice else None


def create_attachment_tool(state):
    @tool("process_attachments", return_direct=False)
    def process_attachments(query: str) -> str:
        """This gets data/string from an attachment :)"""
        logging.info("calling process_attachments")
        session = state.get('session')
        session_pdf_attachment = session.env['ir.attachment'].search([
            ('res_model', '=', 'ai.quest.session'),
            ('res_id', '=', session.id),
            ('mimetype', '=', 'application/pdf'),
        ], limit=1)
        if session_pdf_attachment:
            pdf_content = session_pdf_attachment.get_pdf_content()
            return pdf_content

    return process_attachments
