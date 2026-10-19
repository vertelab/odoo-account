# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2026- Vertel Sverige AB (<https://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models

from odoo.addons.report_xlsx_helper.report.report_xlsx_format import FORMATS


class OutstandingStatementXlsxVrtl(models.AbstractModel):
    """Mirror the HTML statement's column set in the XLSX export.

    OCA's XLSX layout is ``Reference / Date / Due Date / Description /
    Original / Open Amount / Balance`` and it bypasses the QWeb template
    entirely, so the Vertel *Reconciled* column that
    ``views/outstanding_statement.xml`` adds to the HTML report is missing
    from the spreadsheet. Reading the same statement in Excel therefore
    gave a different picture than the PDF/HTML.

    We keep OCA's column *order* (nothing shifts position) but turn the
    *Open Amount* column into *Reconciled* and *Remaining*, and renumber the
    following ``Balance`` column from 6 to 7.

    Column values come from the lines prepared by
    ``report.partner_statement.outstanding_statement`` (see
    ``report/outstanding_statement.py``): ``reconciled_amount`` is either
    OCA's native Q3 column or, for rows that never pass through
    ``_get_account_display_lines`` (prior/ending rows), derived in
    ``_get_report_values``. ``open_amount`` is the signed remaining amount.
    """

    _inherit = "report.p_s.report_outstanding_statement_xlsx"

    def _get_report_label(self):
        return "Utestående uttalande"

    def create_xlsx_report(self, docids, data):
        """Run the whole render with ``active_ids`` in the environment context.

        ``report_xlsx`` calls ``generate_xlsx_report`` on ``self`` — the record
        set built by ``_get_objs_for_report`` — so a ``with_context`` there
        would be lost. ``create_xlsx_report`` is the outermost hook we own, so
        the context is set here before anything else runs. The ``data``
        normalisation lives in ``_get_report_values`` (``outstanding_statement
        .py``) so the same defaults cover every render path.
        """
        ids = [getattr(obj, "id", obj) for obj in (docids or [])]
        if not isinstance(docids, (list, tuple)):
            ids = [docids]
        if ids:
            self = self.with_context(active_ids=ids, active_model="res.partner")
        return super().create_xlsx_report(docids, data)

    def _get_currency_header_row_data(self, partner, currency, data):
        # Same order as the QWeb table in views/outstanding_statement.xml:
        # Reference, Date, Due Date, Description, Original, Reconciled,
        # Remaining, Balance.
        return [
            {
                "col_pos": col_pos,
                "sheet_func": "write",
                "args": args,
            }
            for col_pos, args in enumerate(
                [
                    ("Referensnummer", FORMATS["format_theader_yellow_center"]),
                    ("Datum", FORMATS["format_theader_yellow_center"]),
                    ("Förfallodatum", FORMATS["format_theader_yellow_center"]),
                    ("Beskrivning", FORMATS["format_theader_yellow_center"]),
                    ("Ursprungligt", FORMATS["format_theader_yellow_center"]),
                    ("Avstämt", FORMATS["format_theader_yellow_center"]),
                    ("Kvarstående", FORMATS["format_theader_yellow_center"]),
                    ("Saldo", FORMATS["format_theader_yellow_center"]),
                ]
            )
        ]

    def _get_currency_line_row_data(self, partner, currency, data, line):
        format_tcell_left = FORMATS["format_tcell_left"]
        format_tcell_date_left = FORMATS["format_tcell_date_left"]
        format_distributed = FORMATS["format_distributed"]
        current_money_format = FORMATS["current_money_format"]

        name_to_show = line.get("name") or ""
        ref = line.get("ref") or ""
        if name_to_show in ("", "/"):
            name_to_show = ref
        elif ref and ref not in name_to_show:
            name_to_show = ref

        # Every row produced by _get_report_values carries these two keys;
        # .get() keeps the export alive if a future OCA row type slips in.
        reconciled = line.get("reconciled_amount", 0.0)
        remaining = line.get("open_amount", 0.0)

        return [
            {
                "col_pos": col_pos,
                "sheet_func": "write",
                "args": args,
            }
            for col_pos, args in enumerate(
                [
                    (line.get("move_id") or "", format_tcell_left),
                    (line.get("date") or "", format_tcell_date_left),
                    (line.get("date_maturity") or "", format_tcell_date_left),
                    (name_to_show, format_distributed),
                    (line.get("amount") or 0.0, current_money_format),
                    (reconciled, current_money_format),
                    (remaining, current_money_format),
                    (line.get("balance") or 0.0, current_money_format),
                ]
            )
        ]

    def _get_currency_footer_row_data(self, partner, currency, data):
        # OCA writes the ending balance in column 6; with the extra column
        # it moves to 7 so the figure stays under "Balance".
        return [
            {
                "col_pos": 2,
                "sheet_func": "merge_range",
                "span": 3,
                "args": ("Slutsumma", FORMATS["format_tcell_left"]),
            },
            {
                "col_pos": 7,
                "sheet_func": "write",
                "args": (
                    data.get("data", {})
                    .get(partner.id, {})
                    .get("currencies", {})
                    .get(currency.id, {})
                    .get("amount_due", 0.0),
                    FORMATS["current_money_format"],
                ),
            },
        ]

    def _size_columns(self, sheet, data):
        for i in range(8):
            sheet.set_column(0, i, 20)
