# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2025- Vertel AB (<https://vertel.se>).
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
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models


class AgedPartnerBalanceXslxSorted(models.AbstractModel):
    """Extend OCA Aged Partner Balance XLSX report with alphabetical sorting."""

    _inherit = "report.a_f_r.report_aged_partner_balance_xlsx"
    _description = "Aged Partner Balance XLSX Report (Sorted)"

    def _generate_report_content(self, workbook, report, data, report_data):
        """Same as OCA but with partners sorted alphabetically by name."""
        res_data = self.env[
            "report.account_financial_report.aged_partner_balance"
        ]._get_report_values(report, data)
        show_move_line_details = res_data["show_move_lines_details"]
        aged_partner_balance = res_data["aged_partner_balance"]
        if not show_move_line_details:
            for account in aged_partner_balance:
                self.write_array_title(
                    account["code"] + " - " + account["name"], report_data
                )
                self.write_array_header(report_data)
                # Sort partners alphabetically
                sorted_partners = sorted(
                    account["partners"],
                    key=lambda p: (p["name"] or "").lower()
                )
                for partner in sorted_partners:
                    self.write_line_from_dict(partner, report_data)
                self.write_account_footer_from_dict(
                    report, account, ("Total"),
                    "field_footer_total",
                    report_data["formats"]["format_header_right"],
                    report_data["formats"]["format_header_amount"],
                    False, report_data,
                )
                self.write_account_footer_from_dict(
                    report, account, ("Percents"),
                    "field_footer_percent",
                    report_data["formats"]["format_right_bold_italic"],
                    report_data["formats"]["format_percent_bold_italic"],
                    True, report_data,
                )
                report_data["row_pos"] += 2
        else:
            for account in aged_partner_balance:
                self.write_array_title(
                    account["code"] + " - " + account["name"], report_data
                )
                # Sort partners alphabetically
                sorted_partners = sorted(
                    account["partners"],
                    key=lambda p: (p["name"] or "").lower()
                )
                for partner in sorted_partners:
                    self.write_array_title(partner["name"], report_data)
                    self.write_array_header(report_data)
                    for line in partner["move_lines"]:
                        self.write_line_from_dict(line, report_data)
                    self.write_ending_balance_from_dict(partner, report_data)
                    report_data["row_pos"] += 1
                self.write_account_footer_from_dict(
                    report, account, ("Total"),
                    "field_footer_total",
                    report_data["formats"]["format_header_right"],
                    report_data["formats"]["format_header_amount"],
                    False, report_data,
                )
                self.write_account_footer_from_dict(
                    report, account, ("Percents"),
                    "field_footer_percent",
                    report_data["formats"]["format_right_bold_italic"],
                    report_data["formats"]["format_percent_bold_italic"],
                    True, report_data,
                )
                report_data["row_pos"] += 2
