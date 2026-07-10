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

from odoo import api, models


class AgedPartnerBalanceReportSorted(models.AbstractModel):
    """Extend OCA Aged Partner Balance report with alphabetical partner sorting."""

    _inherit = "report.account_financial_report.aged_partner_balance"
    _description = "Aged Partner Balance Report (Sorted)"

    def _create_account_list(
        self,
        ag_pb_data,
        accounts_data,
        partners_data,
        journals_data,
        show_move_line_details,
        date_at_oject,
    ):
        """Same as OCA but with partners sorted alphabetically by name."""
        aged_partner_data = []
        interval_lines = self.env.context["age_partner_config"].line_ids
        for account in accounts_data.values():
            acc_id = account["id"]
            account.update(
                {
                    "residual": ag_pb_data[acc_id]["residual"],
                    "current": ag_pb_data[acc_id]["current"],
                    "30_days": ag_pb_data[acc_id]["30_days"],
                    "60_days": ag_pb_data[acc_id]["60_days"],
                    "90_days": ag_pb_data[acc_id]["90_days"],
                    "120_days": ag_pb_data[acc_id]["120_days"],
                    "older": ag_pb_data[acc_id]["older"],
                    "partners": [],
                }
            )
            for interval_line in interval_lines:
                account[interval_line] = ag_pb_data[acc_id][interval_line]

            # Collect partners into a list first so we can sort them
            partner_list = []
            for prt_id in ag_pb_data[acc_id]:
                if isinstance(prt_id, int):
                    partner = {
                        "id": prt_id,
                        "name": partners_data[prt_id]["name"],
                        "residual": ag_pb_data[acc_id][prt_id]["residual"],
                        "current": ag_pb_data[acc_id][prt_id]["current"],
                        "30_days": ag_pb_data[acc_id][prt_id]["30_days"],
                        "60_days": ag_pb_data[acc_id][prt_id]["60_days"],
                        "90_days": ag_pb_data[acc_id][prt_id]["90_days"],
                        "120_days": ag_pb_data[acc_id][prt_id]["120_days"],
                        "older": ag_pb_data[acc_id][prt_id]["older"],
                    }
                    for interval_line in interval_lines:
                        partner[interval_line] = ag_pb_data[acc_id][prt_id][
                            interval_line
                        ]
                    if show_move_line_details:
                        move_lines = []
                        for ml in ag_pb_data[acc_id][prt_id]["move_lines"]:
                            ml.update(
                                {
                                    "journal": journals_data[ml["jnl_id"]]["code"],
                                    "account": accounts_data[ml["acc_id"]]["code"],
                                }
                            )
                            self._compute_maturity_date(ml, date_at_oject)
                            move_lines.append(ml)
                        move_lines = sorted(move_lines, key=lambda k: (k["date"]))
                        partner.update({"move_lines": move_lines})
                    partner_list.append(partner)

            # Sort partners alphabetically by name (case-insensitive)
            partner_list.sort(key=lambda p: (p["name"] or "").lower())
            account["partners"] = partner_list
            aged_partner_data.append(account)
        return aged_partner_data

    @api.model
    def _get_report_values(self, docids, data):
        """
        Extend OCA report values with click domain on partners
        so clicking a partner name opens only the invoices
        included in this specific report run.
        """
        res = super()._get_report_values(docids, data)
        aged_partner_balance = res.get("aged_partner_balance", [])
        wizard = self.env[data["wizard_name"]].browse(data["wizard_id"])
        account_ids = wizard.account_ids.ids or []
        date_at = data.get("date_at")
        only_posted = data.get("only_posted_moves", True)
        company_id = data.get("company_id")
        date_from = data.get("date_from")

        for account in aged_partner_balance:
            for partner in account.get("partners", []):
                domain_list = []
                domain_list.append([
                    "partner_id", "=", partner.get("id", 0)
                ])
                if account_ids:
                    domain_list.append([
                        "account_id", "in", account_ids
                    ])
                if date_at:
                    domain_list.append([
                        "date", "<=", date_at
                    ])
                if date_from:
                    domain_list.append([
                        "date", ">", date_from
                    ])
                if company_id:
                    domain_list.append([
                        "company_id", "=", company_id
                    ])
                # Only show unreconciled/partially reconciled lines
                domain_list.append([
                    "reconciled", "=", False
                ])
                if only_posted:
                    domain_list.append([
                        "move_id.state", "=", "posted"
                    ])
                import json
                partner["click_domain"] = json.dumps(domain_list)
        return res
