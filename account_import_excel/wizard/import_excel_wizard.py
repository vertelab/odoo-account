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

        excel_file = BytesIO(self.excel_file)
        try:
            wb = load_workbook(excel_file)
        except Exception as e:
            raise UserError(f"The file given could not be read as an Excel file!\n\n{e}")

        for sheet in wb:
            for row in sheet.iter_rows(values_only=True,max_row=1000,max_col=100):
                _logger.error(f"{row=}")
                



