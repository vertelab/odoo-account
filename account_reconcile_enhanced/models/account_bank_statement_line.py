# Copyright 2026 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

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
        # The counterpart line is booked at its full residual, so the amount
        # still to be covered is exactly the discount. Passing it as
        # ``open_balance`` makes the core helper emit the discount base line
        # and skip the exchange difference line, keeping the entry balanced.
        open_balance = line.amount_residual - line.discount_balance

        epd_values = self.env[
            "account.move"
        ]._get_invoice_counterpart_amls_for_early_payment_discount(
            aml_values_list,
            open_balance,
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
        """Inject the early payment discount lines into the reconcile data.

        ``_get_reconcile_line`` attaches the discount lines under the
        ``epd_lines`` key. They are injected as regular entries of ``data`` so
        that the standard implementation creates them inside its own balanced
        context, together with the counterpart lines they belong to.
        """
        has_epd = any(line_vals.get("epd_lines") for line_vals in data)
        prepared = []
        for line_vals in data:
            epd_lines = line_vals.pop("epd_lines", None)
            if has_epd and line_vals.get("kind") == "suspense":
                # The discount lines replace the suspense line: keeping both
                # would leave the entry unbalanced.
                continue
            prepared.append(line_vals)
            if epd_lines:
                prepared.extend(epd_lines)
        return super()._reconcile_bank_line_edit(prepared)
