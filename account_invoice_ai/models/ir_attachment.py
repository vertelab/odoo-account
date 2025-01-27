from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from langchain_community.document_loaders.parsers.pdf import PyMuPDFParser
from langchain_core.documents.base import Blob
import fitz
from PIL import Image
import pytesseract
import io
import warnings

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def get_pdf_content(self):
        pdf_path = self._full_path(self.store_fname)
        blob = Blob.from_path(pdf_path)
        parser = PyMuPDFParser()
        extracted_text = ""

        # Suppress the specific UserWarning from PyMuPDFParser
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning,
                                    module="langchain_community.document_loaders.parsers.pdf")

            try:
                # First attempt: PyMuPDFParser
                docs_lazy = parser.lazy_parse(blob)
                all_pages = []
                empty_pages = []

                for index, doc in enumerate(docs_lazy, start=1):
                    content = doc.page_content.strip()
                    if content:
                        all_pages.append((index, content))
                    else:
                        empty_pages.append(index)
                        _logger.info(f"Empty content detected on page {index}, will attempt OCR for this page")

                # If we have any successfully parsed pages, combine them
                if all_pages:
                    extracted_text = "\n\n".join([f"Page {page_num}:\n{content}"
                                                  for page_num, content in all_pages])

                # If we have any empty pages, attempt OCR only on those specific pages
                if empty_pages:
                    ocr_text = self._extract_text_from_specific_pages(pdf_path, empty_pages)
                    if ocr_text:
                        extracted_text = (extracted_text + "\n\n" + ocr_text) if extracted_text else ocr_text

            except Exception as e:
                _logger.error(f"Error in PyMuPDFParser processing: {e}", exc_info=True)
                # Fallback to full OCR only if initial parsing completely failed
                extracted_text = self._extract_text_from_pdf_image(pdf_path)

        if not extracted_text.strip():
            _logger.warning("No content could be extracted from the PDF using any method")
            raise UserError(_("Unable to extract any content from the PDF document"))

        return extracted_text

    def _extract_text_from_specific_pages(self, pdf_path, page_numbers):
        """Extract text using OCR from specific pages only."""
        try:
            pdf_document = fitz.open(pdf_path)
            all_text = []

            for page_num in page_numbers:
                if 1 <= page_num <= len(pdf_document):
                    page = pdf_document[page_num - 1]  # Convert to 0-based index
                    image_list = page.get_images(full=True)

                    if image_list:
                        page_text = []
                        for img_index, img in enumerate(image_list):
                            xref = img[0]
                            base_image = pdf_document.extract_image(xref)
                            image_bytes = base_image["image"]

                            image = Image.open(io.BytesIO(image_bytes))
                            text = pytesseract.image_to_string(image)
                            if text.strip():
                                page_text.append(f"Image {img_index + 1}:\n{text}")

                        if page_text:
                            all_text.append(f"Page {page_num} (OCR):\n" + "\n".join(page_text))
                    else:
                        _logger.info(f"No images found on page {page_num}")

            pdf_document.close()
            return "\n\n".join(all_text) if all_text else ""

        except Exception as e:
            _logger.error(f"Error in selective OCR processing: {e}", exc_info=True)
            return ""

    def _extract_text_from_pdf_image(self, pdf_path):
        """Full PDF OCR processing."""
        try:
            pdf_document = fitz.open(pdf_path)
            all_text = []

            for page_number in range(len(pdf_document)):
                page = pdf_document[page_number]
                image_list = page.get_images(full=True)

                if image_list:
                    for img_index, img in enumerate(image_list):
                        xref = img[0]
                        base_image = pdf_document.extract_image(xref)
                        image_bytes = base_image["image"]
                        image = Image.open(io.BytesIO(image_bytes))
                        text = pytesseract.image_to_string(image)
                        if text.strip():
                            all_text.append(f"Page {page_number + 1}, Image {img_index + 1}:\n{text}")
                else:
                    _logger.info(f"No images found on page {page_number + 1}")

            pdf_document.close()
            return "\n\n".join(all_text) if all_text else ""

        except Exception as e:
            _logger.error(f"Error in full OCR processing: {e}", exc_info=True)
            raise UserError(_("Error extracting text from PDF images: %s") % str(e))
