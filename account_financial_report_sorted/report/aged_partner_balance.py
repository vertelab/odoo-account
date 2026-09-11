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
from datetime import date, datetime

from odoo import api, models


class AgedPartnerBalanceReportSorted(models.AbstractModel):
    """Extend OCA Aged Partner Balance report with alphabetical partner sorting."""

    _inherit = "report.account_financial_report.aged_partner_balance"
    _description = "Aged Partner Balance Report (Sorted)"

    # Document types the "Invoiced" smart button on the contact uses; see
    # res.partner.action_view_partner_invoices and
    # account.action_move_out_invoice_type.
    INVOICE_MOVE_TYPES = ("out_invoice", "out_refund")

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

    def _get_report_computed_lines(self, data):
        """OCA's own move-line selection for this report run.

        Calls the report's ``_get_move_lines_data`` with the exact arguments the
        report used, so the result already carries the as-of-date handling
        (``_recalculate_move_lines`` adds back amounts reconciled after a
        backdated report date).
        """
        date_at = data.get("date_at")
        date_at_object = (
            datetime.strptime(date_at, "%Y-%m-%d").date() if date_at else date.today()
        )
        age_partner_configuration = self.env[
            "account.age.report.configuration"
        ].browse(data.get("age_partner_config_id"))
        ag_pb_data, _accounts, _partners, _journals = self.with_context(
            age_partner_config=age_partner_configuration
        )._get_move_lines_data(
            data.get("company_id"),
            data.get("account_ids") or [],
            data.get("partner_ids") or [],
            date_at_object,
            data.get("date_from"),
            data.get("only_posted_moves", True),
            True,  # show_move_line_details: we need the underlying lines
        )
        return ag_pb_data

    def _get_open_moves_per_account_partner(self, data):
        """Return {(account_id, partner_id): sorted list of account.move ids}

        The moves are exactly the invoices behind the partner's balance for this
        report run: the report's own computed lines (as of the report date,
        including lines settled after a backdated date) restricted to invoice
        documents. Bank/payment entries that merely happen to be unreconciled on
        the receivable account are never listed.
        """
        ag_pb_data = self._get_report_computed_lines(data)

        # (account_id, partner_id) -> underlying account.move.line ids
        line_ids_by_key = defaultdict(list)
        for acc_id, partner_map in ag_pb_data.items():
            if not isinstance(acc_id, int):
                continue
            for prt_id, prt_data in partner_map.items():
                if not isinstance(prt_id, int) or not isinstance(prt_data, dict):
                    continue
                for ml in prt_data.get("move_lines") or []:
                    line = ml.get("line_rec")
                    if line:
                        line_ids_by_key[(acc_id, prt_id)].append(line.id)

        if not line_ids_by_key:
            return {}

        # Resolve line -> move in one batch (prefetch), then keep invoices only.
        lines = self.env["account.move.line"].browse(
            [lid for line_ids in line_ids_by_key.values() for lid in line_ids]
        )
        line_to_move = {line.id: line.move_id for line in lines}

        mapping = {}
        for key, line_ids in line_ids_by_key.items():
            mapping[key] = sorted(
                {
                    line_to_move[lid].id
                    for lid in line_ids
                    if line_to_move[lid].move_type in self.INVOICE_MOVE_TYPES
                }
            )
        return mapping

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
