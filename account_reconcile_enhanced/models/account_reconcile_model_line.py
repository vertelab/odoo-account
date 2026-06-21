# Copyright 2026 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import re
from math import copysign

from odoo import _, api, models
from odoo.exceptions import RedirectWarning


class AccountReconcileModelLine(models.Model):
    _inherit = "account.reconcile.model.line"

    def _apply_in_bank_widget(
        self, residual_amount_currency, partner, st_line
    ):
        """Prepare a dictionary for creating a new journal item from this
        reconcile model line, used in the bank reconciliation widget.

        Adds support for amount_type 'percentage_st_line' and 'regex'.
        """
        self.ensure_one()
        currency = (
            st_line.foreign_currency_id
            or st_line.journal_id.currency_id
            or st_line.company_currency_id
        )

        # First, try advanced amount types
        if self.amount_type == "percentage_st_line":
            (
                _transaction_amount,
                _transaction_currency,
                journal_amount,
                journal_currency,
                company_amount,
                company_currency,
            ) = st_line._get_accounting_amounts_and_currencies()
            aml_values = {
                "currency_id": journal_currency.id,
                "amount_currency": currency.round(
                    -journal_amount * self.amount / 100.0
                ),
                "balance": company_currency.round(
                    -company_amount * self.amount / 100.0
                ),
            }
            aml_values.update(self._prepare_aml_vals(partner))
            if not aml_values.get("name"):
                aml_values["name"] = st_line.payment_ref
            return aml_values

        elif self.amount_type == "regex":
            amount_currency = self._get_amount_currency_by_regex(
                st_line, residual_amount_currency, self.amount_string
            )
            balance = self._get_amount_currency_by_regex(
                st_line,
                residual_amount_currency,
                self.amount_string,
                use_company_currency=True,
            )
            aml_values = {
                "currency_id": currency.id,
                "amount_currency": amount_currency,
                "balance": balance,
            }
            aml_values.update(self._prepare_aml_vals(partner))
            if not aml_values.get("name"):
                aml_values["name"] = st_line.payment_ref
            return aml_values

        # Fall back to OCA default behavior (handles percentage and fixed)
        return super()._apply_in_bank_widget(
            residual_amount_currency, partner, st_line
        )

    @api.model
    def _get_amount_currency_by_regex(
        self, st_line, residual_amount_currency, amount_string,
        use_company_currency=False
    ):
        """Extract an amount from the statement line text using a regex pattern.
        The first capture group must contain the numeric amount.

        :param st_line: The bank statement line
        :param residual_amount_currency: The residual amount (used for sign)
        :param amount_string: The regex pattern with a capture group
        :param use_company_currency: If True, convert to company currency
        :return: The extracted amount as float
        """
        sign = 1 if residual_amount_currency > 0.0 else -1
        transaction_details = (
            json.dumps(st_line.transaction_details)
            if st_line.transaction_details
            else False
        )
        for target_field in (
            st_line.payment_ref,
            transaction_details,
            st_line.narration,
        ):
            if not target_field:
                continue
            if match := re.search(amount_string, target_field):
                try:
                    extracted_match_group = re.search(
                        r"\d+[,.]?\d*", match.group(1)
                    )
                    extracted_balance = float(
                        extracted_match_group.group().replace(",", ".")
                    )
                    result = copysign(
                        extracted_balance * sign, residual_amount_currency
                    )
                    if use_company_currency and st_line.foreign_currency_id:
                        result = st_line.foreign_currency_id._convert(
                            result,
                            st_line.company_currency_id,
                            st_line.company_id,
                            st_line.date,
                        )
                    return result
                except IndexError:
                    raise RedirectWarning(
                        _(
                            "The regular expression for capturing the counterpart "
                            "amount appears to be incorrectly formatted.\n"
                            "Please make sure that the part of the regex capturing "
                            "the amount is the first (or only) one in parentheses, "
                            "for example: BRT: ([\\d,.]+)."
                        ),
                        self.model_id._get_records_action(),
                        _("Open reconcile model"),
                    )
                except AttributeError:
                    raise RedirectWarning(
                        _(
                            "The regular expression for capturing the counterpart "
                            "amount appears to be incorrectly formatted.\n"
                            "Please make sure that the part of the regex capturing "
                            "the amount (in parentheses) cannot capture an empty "
                            "value."
                        ),
                        self.model_id._get_records_action(),
                        _("Open reconcile model"),
                    )
        return 0.0
