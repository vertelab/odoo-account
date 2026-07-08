"""BAS Chart Template — importable from Excel."""

from odoo import api, fields, models


class AccountChartTemplate(models.Model):
    _name = "account.chart.template"
    _description = "Account Chart Template"
    _order = "year desc, name"

    name = fields.Char(string="Name", required=True)
    year = fields.Integer(string="Year", help="BAS version year (e.g. 2025)")
    description = fields.Text(string="Description")
    account_line_ids = fields.One2many(
        "account.chart.template.line",
        "template_id",
        string="Accounts",
    )
    active = fields.Boolean(default=True)

    def import_from_excel(self, file_data):
        """Import chart of accounts from BAS Excel file.

        Expected columns: code, name, type, sru_code, notes
        """
        self.ensure_one()
        try:
            import base64
            import io

            import xlrd  # or openpyxl for .xlsx
        except ImportError:
            from odoo.exceptions import UserError
            raise UserError(
                "xlrd or openpyxl is required for Excel import. "
                "Install with: pip install xlrd openpyxl"
            )

        # Clear existing lines
        self.account_line_ids.unlink()

        data = base64.b64decode(file_data)
        workbook = xlrd.open_workbook(file_contents=data)
        sheet = workbook.sheet_by_index(0)

        lines = []
        for row_idx in range(1, sheet.nrows):  # Skip header
            code = str(sheet.cell_value(row_idx, 0)).strip()
            name = str(sheet.cell_value(row_idx, 1)).strip()
            account_type = str(sheet.cell_value(row_idx, 2)).strip() if sheet.ncols > 2 else ""
            sru_code = str(sheet.cell_value(row_idx, 3)).strip() if sheet.ncols > 3 else ""

            if not code:
                continue

            lines.append((0, 0, {
                "code": code,
                "name": name,
                "account_type": account_type,
                "sru_code": sru_code,
            }))

        self.write({"account_line_ids": lines})
        return len(lines)


class AccountChartTemplateLine(models.Model):
    _name = "account.chart.template.line"
    _description = "Account Chart Template Line"
    _order = "code"

    template_id = fields.Many2one(
        "account.chart.template",
        string="Template",
        required=True,
        ondelete="cascade",
    )
    code = fields.Char(string="Account Code", required=True)
    name = fields.Char(string="Account Name", required=True)
    account_type = fields.Char(string="Account Type")
    sru_code = fields.Char(string="SRU Code")
