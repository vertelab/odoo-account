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

from collections import defaultdict
from datetime import datetime

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
        res = super()._get_report_values(docids, data)
        # Build, per (account, partner), the list of account.move ids that make
        # up that partner's row in THIS report run, so clicking a partner name
        # opens exactly the invoices/account.moves behind the aged balance.
        self._attach_move_ids_to_partners(res, data)
        return res

    def _get_ml_field_domain(self, data):
        """Reuse OCA's selection domain for move lines (accounts, company,
        reconciliation, posting state and date_from).
        """
        account_ids = data.get("account_ids") or []
        partner_ids = data.get("partner_ids") or []
        company_id = data.get("company_id")
        date_from = data.get("date_from")
        only_posted = data.get("only_posted_moves", True)

        domain = self._get_move_lines_domain_not_reconciled(
            company_id, account_ids, partner_ids, only_posted, date_from
        )
        return domain

    def _get_open_moves_per_account_partner(self, data):
        """Return {(account_id, partner_id): sorted list of account.move ids}

        The moves are those whose open lines (reconciled=False) match the exact
        selection the report uses (same accounts, company, posting state and
        date_from), dated <= the report date. This reproduces per account+partner
        the invoices behind the aged balance shown in this report run.
        """
        date_at = data.get("date_at")
        date_at_date = None
        if date_at:
            date_at_date = datetime.strptime(date_at, "%Y-%m-%d").date()

        domain = self._get_ml_field_domain(data)
        move_lines = self.env["account.move.line"].search_read(
            domain=domain,
            fields=["id", "account_id", "partner_id", "move_id", "date"],
        )
        mapping = defaultdict(set)
        for line in move_lines:
            acc_id = line["account_id"][0] if line["account_id"] else None
            prt_id = line["partner_id"][0] if line["partner_id"] else None
            move_id = line["move_id"][0] if line["move_id"] else None
            if acc_id is None or prt_id is None or move_id is None:
                continue
            # The report only counts lines dated <= report date
            if date_at_date is not None and line["date"] > date_at_date:
                continue
            mapping[(acc_id, prt_id)].add(move_id)
        return {key: sorted(ids) for key, ids in mapping.items()}

    def _attach_move_ids_to_partners(self, res, data):
        aged_partner_balance = res.get("aged_partner_balance", [])
        mapping = self._get_open_moves_per_account_partner(data)
        for account in aged_partner_balance:
            acc_id = account.get("id")
            for partner in account.get("partners", []):
                prt_id = partner.get("id")
                move_ids = mapping.get((acc_id, prt_id), [])
                partner["move_ids"] = move_ids
                if move_ids:
                    # Same python-domain-string format OCA uses for clickable
                    # report elements (res-model + domain).
                    partner["move_click_domain"] = (
                        "[('id', 'in', [%s])]"
                        % ", ".join(str(i) for i in move_ids)
                    )
                else:
                    partner["move_click_domain"] = "[('id', 'in', [])]"
        return res
