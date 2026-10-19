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

from odoo import api, fields, models
from odoo.tools import float_is_zero

# Sign convention (T/11336):
#   Customer owes us money  -> POSITIVE
#   Customer has credit     -> NEGATIVE
#
# OCA's outstanding_statement exposes `debit` and `credit` as two positive
# columns and `amount = debit - credit`. For a receivable account that is
# already the correct sign, but for a payable account (vendor) it is
# inverted. We normalise on account_type so that the same rule holds for
# customers and vendors alike.


class OutstandingStatementVrtl(models.AbstractModel):
    _inherit = "report.partner_statement.outstanding_statement"

    def _vrtl_sign(self, account_type):
        """Return +1 for receivable, -1 for payable.

        Receivable lines: debit increases what the customer owes (positive).
        Payable lines: credit increases what we owe the vendor, which is the
        mirror image — so we flip the sign to keep "we are owed" positive.
        """
        return -1.0 if account_type == "liability_payable" else 1.0

    def _get_account_display_lines(
        self, company_id, partner_ids, date_start, date_end, account_type
    ):
        """Fetch OCA's rows and normalise signs + add the reconciled column."""
        res = super()._get_account_display_lines(
            company_id, partner_ids, date_start, date_end, account_type
        )
        sign = self._vrtl_sign(account_type)
        for lines in res.values():
            for line in lines:
                debit = line.get("debit") or 0.0
                credit = line.get("credit") or 0.0
                open_amount = line.get("open_amount") or 0.0

                # OCA keeps debit/credit as two positive columns. Rebuild a
                # single signed amount and apply the account-type sign.
                line["amount"] = (debit - credit) * sign
                line["open_amount"] = open_amount * sign

                # "Reconciled" = how much of the original transaction has
                # already been settled. Original minus remaining.
                line["reconciled_amount"] = line["amount"] - line["open_amount"]

                # Keep the raw columns for backwards compatibility, but make
                # them signed so nothing downstream shows a stray positive
                # credit note.
                line["debit"] = debit * sign
                line["credit"] = -credit * sign
        return res

    def _add_currency_line(self, line, currency):
        """Same filter as OCA, but on the normalised open_amount."""
        if float_is_zero(
            line["open_amount"], precision_rounding=currency.rounding
        ):
            return []
        return [line]

    @api.model
    def _get_report_values(self, docids, data=None):
        """Guarantee ``reconciled_amount`` on every rendered row.

        OCA's template ``partner_statement.outstanding_balance`` is inherited
        by this module and renders ``line['reconciled_amount']`` before the
        open amount cell. ``_get_account_display_lines`` only reaches rows
        that carry an ``id``; the prior/ending/reconciled rows of the
        statement (and any other row list that ends up in
        ``currency[line_type]``) never pass through it, which raised
        ``KeyError: 'reconciled_amount'`` for those partners.

        OCA's standard ``outstanding_statement.py`` also ships a *native*
        ``reconciled_amount`` column in Q3 (``debit - credit - open_amount``).
        When it is present we reuse it verbatim; only when a row lacks it do
        we derive it, so the value always matches the underlying SQL.
        """
        # ``active_ids`` must be present in the context: OCA's
        # ``_get_report_values`` instantiates the statement wizard with
        # ``wiz.create({})`` and the ``number_partner_ids`` default is
        # ``len(self._context.get("active_ids", []))``. ``.get()`` returns
        # ``None`` (not the default) when the key *exists* but is ``None``,
        # so an ``active_ids=None`` context left by the report wizard made
        # the XLSX renderer crash with ``TypeError: object of type
        # 'NoneType' has no len()``.
        ctx = self._vrtl_statement_context(docids)
        if data is None:
            data = {}
        # OCA only builds the wizard when ``company_id`` is missing, and the
        # wizard's ``number_partner_ids`` default does ``len(active_ids)``.
        # Passing ``partner_ids`` in ``data`` makes the guard fire before the
        # wizard is ever created, which is exactly what the XLSX path needs.
        if not data.get("company_id"):
            data["company_id"] = self.env.company.id
        if not data.get("partner_ids"):
            data["partner_ids"] = list(ctx.get("active_ids") or [])
        # The XLSX path passes ``generate_xlsx_report`` data straight through,
        # and ``report_statement_common`` reads ``data["date_end"]`` without a
        # fallback (the HTML path always gets it from the wizard).
        if not data.get("date_end"):
            date_end = data.get("date_to") or fields.Date.context_today(self)
            data["date_end"] = (
                fields.Date.to_date(date_end)
                if isinstance(date_end, str)
                else date_end
            )
        # ``report_statement_common._get_report_values`` indexes every one of
        # these keys without a fallback, so the XLSX renderer (which bypasses
        # the wizard) must get explicit defaults or fail with KeyError.
        defaults = {
            "account_type": "asset_receivable",
            "aging_type": "days",
            "excluded_accounts_ids": [],
            "show_aging_buckets": False,
            "show_only_overdue": False,
            "filter_non_due_partners": True,
            "filter_negative_balances": False,
        }
        for key, value in defaults.items():
            if data.get(key) is None:
                data[key] = value
        values = super(
            OutstandingStatementVrtl, self.with_context(**ctx)
        )._get_report_values(docids, data=data)
        account_type = values.get("account_type")
        for partner_data in (values.get("data") or {}).values():
            for line_currency in (partner_data.get("currencies") or {}).values():
                for key in (
                    "lines",
                    "prior_lines",
                    "ending_lines",
                    "reconciled_lines",
                ):
                    for line in line_currency.get(key) or []:
                        self._vrtl_fill_reconciled_amount(line, account_type)
        return values

    def _vrtl_statement_context(self, docids):
        """Return a context dict with the statement partners in active_ids."""
        partners = None
        if docids:
            partners = docids
        elif self.env.context.get("active_ids"):
            partners = self.env.context["active_ids"]
        ctx = {}
        if partners:
            partners = [int(pid) for pid in partners]
            ctx.update(
                active_ids=partners,
                active_model="res.partner",
                active_id=partners[0],
            )
        else:
            # Never leave a None behind: OCA calls len() on the value.
            ctx["active_ids"] = []
        return ctx

    def _vrtl_fill_reconciled_amount(self, line, account_type):
        """Add ``reconciled_amount`` only if it is missing (signed)."""
        if "reconciled_amount" in line:
            return line
        sign = self._vrtl_sign(account_type)
        amount = line.get("amount")
        open_amount = line.get("open_amount")
        if amount is None or open_amount is None:
            debit = line.get("debit") or 0.0
            credit = line.get("credit") or 0.0
            amount = (debit - credit) * sign
            open_amount = (line.get("open_amount") or 0.0) * sign
        line["reconciled_amount"] = amount - open_amount
        return line
