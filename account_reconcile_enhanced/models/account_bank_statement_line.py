# Copyright 2026 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import Counter

from odoo import Command, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _get_epd_aml_values_list(self, line):
        """Return the ``aml_values`` consumed by the core early payment
        discount helper for a single counterpart line.

        The core helper ``_get_invoice_counterpart_amls_for_early_payment_discount``
        expects the *matched* amounts, i.e. the negated residual of the invoice
        line, exactly like the ``account_accountant`` widget does.
        """
        return [
            {
                "aml": line,
                "amount_currency": -line.amount_currency,
                "balance": -line.amount_residual,
            }
        ]

    def _get_epd_lines(self, line):
        """Build the early payment discount counterpart lines for ``line``.

        Returns a list of reconcile-data dicts (discount line + exchange
        difference line when relevant), or an empty list when the invoice is
        not eligible.
        """
        invoice = line.move_id
        transaction_currency = self.foreign_currency_id or self.currency_id
        if not invoice._is_eligible_for_early_payment_discount(
            transaction_currency, self.date
        ):
            return []

        aml_values_list = self._get_epd_aml_values_list(line)
        # The core helper subtracts every discount line it builds from
        # ``open_balance`` and books whatever is left on an exchange
        # difference line. To keep the entry balanced that remainder must be
        # zero, so ``open_balance`` has to be the discount amount itself --
        # not the invoice residual minus the discounted balance, which is the
        # paid amount and leaves a bogus exchange line behind.
        epd_values = self.env[
            "account.move"
        ]._get_invoice_counterpart_amls_for_early_payment_discount(
            aml_values_list,
            open_balance=0.0,
        )
        # Recompute the discount total from the produced lines and ask the
        # helper again with that exact amount, so no exchange difference is
        # generated.
        discount_balance = sum(
            vals.get("balance") or 0.0
            for key in ("base_lines", "tax_lines", "term_lines")
            for vals in epd_values[key]
        )
        if discount_balance:
            epd_values = self.env[
                "account.move"
            ]._get_invoice_counterpart_amls_for_early_payment_discount(
                aml_values_list,
                open_balance=discount_balance,
            )

        lines = []
        for values in epd_values.values():
            for vals in values:
                balance = vals.get("balance") or 0.0
                account = self.env["account.account"].browse(vals["account_id"])
                partner_id = vals.get("partner_id")
                lines.append(
                    {
                        "account_id": [account.id, account.display_name],
                        "name": vals.get("name"),
                        "partner_id": partner_id
                        and [
                            partner_id,
                            self.env["res.partner"].browse(partner_id).display_name,
                        ],
                        "currency_id": self.company_id.currency_id.id,
                        "line_currency_id": vals.get("currency_id"),
                        "currency_amount": vals.get("amount_currency"),
                        "balance": balance,
                        "debit": balance if balance > 0 else 0.0,
                        "credit": -balance if balance < 0 else 0.0,
                        "amount": balance,
                        "net_amount": balance,
                        "kind": "other",
                        "tax_ids": vals.get("tax_ids", []),
                        "tax_tag_ids": vals.get("tax_tag_ids", []),
                        "tax_repartition_line_id": vals.get("tax_repartition_line_id"),
                        "group_tax_id": vals.get("group_tax_id"),
                        "analytic_distribution": vals.get("analytic_distribution"),
                    }
                )
        return lines

    def _get_reconcile_line(
        self,
        line,
        kind,
        is_counterpart=False,
        max_amount=False,
        from_unreconcile=False,
        move=False,
        is_reconciled=False,
        **kwargs,
    ):
        """Attach the early payment discount lines to the counterpart line.

        OCA's ``account_reconcile_model_oca`` already detects the early payment
        discount and uses the discounted amount to find a matching candidate,
        but that amount is lost afterwards: ``_get_reconcile_line`` always books
        the full residual, letting the discount and the exchange difference end
        up on separate manual entries instead of being part of the
        reconciliation.

        Mirror the ``account_accountant`` widget: keep the counterpart line at
        its full residual and let the core helper generate the discount lines
        that bring the entry back to balance.
        """
        epd_lines = []
        if is_counterpart and not from_unreconcile:
            # ``line`` may be an id or a recordset depending on the caller.
            line_record = (
                line
                if isinstance(line, models.BaseModel)
                else self.env["account.move.line"].browse(line)
            )
            if line_record.move_id:
                epd_lines = self._get_epd_lines(line_record)

        result = super()._get_reconcile_line(
            line,
            kind,
            is_counterpart=is_counterpart,
            # When an early payment discount applies, the counterpart must be
            # booked at its full residual: the discount line generated below
            # brings the entry back to balance. Capping the amount to the paid
            # one (max_amount) would leave the discount unbalanced.
            max_amount=False if epd_lines else max_amount,
            from_unreconcile=from_unreconcile,
            move=move,
            is_reconciled=is_reconciled,
            **kwargs,
        )
        if not epd_lines:
            return result

        # ``account_reconcile_oca`` wraps the result as
        # ``(reconcile_auxiliary_id, vals_list)`` while
        # ``account.reconcile.abstract`` returns a plain ``vals_list``.
        if isinstance(result, tuple):
            auxiliary_id, vals_list = result
        else:
            auxiliary_id, vals_list = None, result

        for vals in vals_list:
            if isinstance(vals, dict):
                vals["epd_lines"] = epd_lines

        return (auxiliary_id, vals_list) if auxiliary_id is not None else vals_list

    def _reconcile_bank_line_edit(self, data):
        """Make sure the early payment discount lines are created once.

        ``_get_reconcile_line`` attaches the discount lines under the
        ``epd_lines`` key on the counterpart row, so the widget can display
        them. Depending on how the widget rebuilt ``data``, those lines reach
        this method either as regular rows of ``data`` *and* as the payload, or
        only as the payload.

        Injecting the payload unconditionally doubles the discount and leaves
        the entry unbalanced, while dropping it unconditionally loses the
        discount. Each payload row is therefore only added when an equivalent
        row is not already part of ``data``.
        """
        present = Counter(
            (
                tuple(v.get("account_id") or ()),
                round(v.get("debit") or 0.0, 6),
                round(v.get("credit") or 0.0, 6),
            )
            for v in data
        )
        prepared = []
        for line_vals in data:
            line_vals = dict(line_vals)
            epd_lines = line_vals.pop("epd_lines", None) or []
            prepared.append(line_vals)
            for epd_line in epd_lines:
                key = (
                    tuple(epd_line.get("account_id") or ()),
                    round(epd_line.get("debit") or 0.0, 6),
                    round(epd_line.get("credit") or 0.0, 6),
                )
                if present[key] > 0:
                    # Already sent as a regular row; adding it would double it.
                    present[key] -= 1
                    continue
                prepared.append(epd_line)
        return super()._reconcile_bank_line_edit(prepared)
