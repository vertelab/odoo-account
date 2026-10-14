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
