import base64
from openpyxl import load_workbook
from io import BytesIO

from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class ImportExcelWizard(models.TransientModel):
    _name = 'import.excel.wizard'
    _description = 'Simpel excel import wizard'

    excel_file = fields.Binary(required=True)

    def load_excel(self):

        excel_file = BytesIO(base64.b64decode(self.excel_file))
        try:
            wb = load_workbook(excel_file)
        except Exception as e:
            raise UserError(f"The file given could not be read as an Excel file!\n\n{e}")
        
        words = {"invoicenumber": "ref", "contact": "partner_id", "product": "product_id", "analytic_accounts": "analytic_accounts_id", "unit": "product_uom_id", "amount": "quantity", "price": "price_unit", "date": "invoice_date_due"}

        for sheet in wb:
            word_index,filterd_fields = self.index_word_filter(sheet,words)
            for row in sheet.iter_rows(values_only=True,min_row=2,max_row=100,max_col=100):
                if not all(r is None for r in row):
                    row_values = [row[i] for i in word_index]
                    data = dict(zip(filterd_fields,row_values))

    def index_word_filter(self,sheet,words):
        first_row = next(sheet.iter_rows(values_only=True,min_row=1,max_row=1))
        word_index = []
        filterd_words_fields = []
        for word in words.keys():
            if word in first_row:
                row_index = first_row.index(word)
                word_index.append(row_index)
                filterd_words_fields.append(words[word])
        return word_index, filterd_words_fields

