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
        import base64
        import io

        from odoo.exceptions import UserError

        try:
            import openpyxl
        except ImportError:
            raise UserError(
                "openpyxl is required for Excel import. "
                "Install with: pip install openpyxl"
            )

        # Clear existing lines
        self.account_line_ids.unlink()

        data = base64.b64decode(file_data)
        try:
            workbook = openpyxl.load_workbook(
                io.BytesIO(data), read_only=True, data_only=True)
        except Exception as exc:
            raise UserError(
                "Could not read the Excel file: %s" % exc) from exc
        sheet = workbook.worksheets[0]

        lines = []
        # Skip header row. read_only mode yields tuples, values_only=True
        # gives raw values per row.
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if not row:
                continue
            code = str(row[0]).strip() if row[0] is not None else ""
            name = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
            account_type = (
                str(row[2]).strip() if len(row) > 2 and row[2] is not None else "")
            sru_code = (
                str(row[3]).strip() if len(row) > 3 and row[3] is not None else "")

            if not code:
                continue

            lines.append((0, 0, {
                "code": code,
                "name": name,
                "account_type": account_type,
                "sru_code": sru_code,
            }))

        workbook.close()
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
