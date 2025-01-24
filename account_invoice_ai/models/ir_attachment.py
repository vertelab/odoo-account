from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError
from langchain.schema import AIMessage, HumanMessage, SystemMessage, BaseMessage
import json
import io
import re

from datetime import datetime
from hashlib import md5
from logging import getLogger
from zlib import compress, decompress
from PIL import Image, PdfImagePlugin
import logging
# from langchain.document_loaders import PyPDFLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents.base import Blob
from langchain_community.document_loaders.parsers import PyMuPDFParser
# from langchain.chains import QAChain
from langchain_community.llms.openai import OpenAIChat, OpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from typing_extensions import List

_logger = logging.getLogger(__name__)


class CVDataExtraction(BaseModel):
    username: str = Field(description="candidate username")
    email: str = Field(description="candidate email")
    profile: str = Field(description="candidate profile description")
    skills: List[str] = Field(description="soft and technical skills")


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def get_pdf_content(self):
        pdf_path = self._full_path(self.store_fname)
        blob = Blob.from_path(pdf_path)

        parser = PyMuPDFParser()

        docs_lazy = parser.lazy_parse(blob)

        # Collect pages into a list with an explicit index
        all_pages = []
        for index, doc in enumerate(docs_lazy, start=1):  # Start indexing from 1 for page numbers
            all_pages.append((index, doc.page_content))

        # Join sorted page content into a single string
        all_pages_text = "\n\n".join([f"Page {page_num}:\n{content}" for page_num, content in all_pages])

        return all_pages_text

