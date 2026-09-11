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

from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


@tagged("post_install", "-at_install")
class TestAgedPartnerDrilldown(TransactionCase):
    """The Aged Partner Balance ages *invoices* only (T/11301, T/11336):

    - the aged amounts and the partner rows must not include unapplied
      payments / customer advances sitting on the receivable account,
    - the clickable partner list must show exactly the invoices behind the
      aged amount, for the report date (backdating included),
    - the Open Items report (where an advance *does* belong) is unaffected.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
                mail_notrack=True,
                tracking_disable=True,
            )
        )
        cls.report = cls.env["report.account_financial_report.aged_partner_balance"]
        cls.open_items_report = cls.env["report.account_financial_report.open_items"]
        cls.company = cls.env.company
        cls.sale_journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.company.id)], limit=1
        )
        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", cls.company.id)], limit=1
        )
        cls.misc_journal = cls.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", cls.company.id)], limit=1
        )
        cls.income_account = cls.env["account.account"].search(
            [("account_type", "in", ("income", "income_other"))], limit=1
        )
        cls.age_config = cls.env["account.age.report.configuration"].create(
            {
                "name": "Drill-down test intervals",
                "line_ids": [(0, 0, {"name": "1-30", "inferior_limit": 30})],
            }
        )

    # ------------------------------------------------------------------ helpers

    def _new_partner(self, name):
        return self.env["res.partner"].create({"name": name})

    def _post_invoice(self, partner, amount, invoice_date, due_date):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "journal_id": self.sale_journal.id,
                "invoice_date": invoice_date,
                "date": invoice_date,
                "invoice_date_due": due_date,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test line",
                            "quantity": 1.0,
                            "price_unit": amount,
                            "account_id": self.income_account.id,
                            "tax_ids": [(5, 0, 0)],
                        },
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def _post_deposit(self, partner, amount, date):
        """Post a bank/deposit journal entry on the partner's receivable account.

        This is an advance / unapplied payment: not a receivable, so it must not
        be aged in this report (it belongs in Open Items / Partner Ledger).
        """
        receivable = partner.property_account_receivable_id
        entry = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.misc_journal.id,
                "date": date,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": receivable.id,
                            "partner_id": partner.id,
                            "credit": amount,
                            "name": "Deposit",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": self.income_account.id,
                            "debit": amount,
                            "name": "Deposit",
                        },
                    ),
                ],
            }
        )
        entry.action_post()
        return entry

    def _prepare_report_data(self, partner, date_at):
        wizard = self.env["aged.partner.balance.report.wizard"].create(
            {
                "date_at": date_at,
                "account_ids": [(6, 0, [partner.property_account_receivable_id.id])],
                "partner_ids": [(6, 0, [partner.id])],
                "target_move": "posted",
                "age_partner_config_id": self.age_config.id,
            }
        )
        data = wizard._prepare_report_data()
        # Simulate the web client, which sends the date back as a string.
        data["date_at"] = date_at.strftime(DEFAULT_SERVER_DATE_FORMAT)
        return wizard, data

    def _report_row(self, partner, date_at):
        wizard, data = self._prepare_report_data(partner, date_at)
        res = self.report._get_report_values(wizard.ids, data)
        for account in res.get("aged_partner_balance", []):
            for row in account.get("partners", []):
                if row.get("id") == partner.id:
                    return row
        return None

    # ------------------------------------------------------------------- tests

    def test_deposit_is_not_aged_but_invoice_is(self):
        """The aged amount is the invoice only; the deposit is not netted in."""
        today = fields.Date.context_today(self.env.user)
        partner = self._new_partner("Aged Invoice And Deposit")
        invoice = self._post_invoice(
            partner, 1000.0, today - timedelta(days=10), today - timedelta(days=5)
        )
        self._post_deposit(partner, 500.0, today - timedelta(days=3))

        row = self._report_row(partner, today)

        self.assertTrue(row, "The partner has an open invoice and must be reported")
        self.assertAlmostEqual(
            row["residual"],
            1000.0,
            2,
            "Only the invoice may be aged; the 500 deposit must not reduce it",
        )
        self.assertEqual(
            row["move_ids"],
            [invoice.id],
            "Only the open invoice should be clickable, not the deposit entry",
        )

    def test_backdated_lists_invoice_paid_after_report_date(self):
        """A backdated run lists an invoice that was open then but is paid now."""
        today = fields.Date.context_today(self.env.user)
        report_date = today - timedelta(days=30)
        partner = self._new_partner("Aged Backdated")
        invoice = self._post_invoice(
            partner, 1000.0, today - timedelta(days=60), report_date
        )

        # Pay the invoice after the report date.
        pay_wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create(
                {
                    "payment_date": today - timedelta(days=10),
                    "journal_id": self.bank_journal.id,
                }
            )
        )
        pay_wizard._create_payments()
        self.assertTrue(
            invoice.line_ids.filtered(
                lambda line: line.account_id == partner.property_account_receivable_id
            ).reconciled,
            "Precondition: the invoice must be settled after the report date",
        )

        backdated = self._report_row(partner, report_date)
        self.assertTrue(backdated, "The invoice was open at the report date")
        self.assertAlmostEqual(backdated["residual"], 1000.0, 2)
        self.assertEqual(backdated["move_ids"], [invoice.id])

        # Fully settled today -> nothing left to age for this partner.
        self.assertFalse(
            self._report_row(partner, today),
            "The settled invoice is no longer open today, so it is not aged",
        )

    def test_deposit_only_partner_is_not_aged(self):
        """A partner whose balance is only an advance is not reported at all."""
        today = fields.Date.context_today(self.env.user)
        partner = self._new_partner("Aged Deposit Only")
        entry = self._post_deposit(partner, 750.0, today - timedelta(days=2))

        self.assertFalse(
            self._report_row(partner, today),
            "An unapplied payment is not a receivable and must not be aged",
        )

        # ... but the Open Items report must still see it (that is where an
        # advance belongs, and it backs the 1510 reconciliation).
        receivable = partner.property_account_receivable_id
        domain = self.open_items_report._get_move_lines_domain_not_reconciled(
            self.company.id, [receivable.id], [partner.id], True, False
        )
        open_lines = self.env["account.move.line"].search(domain).filtered(
            lambda line: line.move_id == entry
        )
        self.assertTrue(
            open_lines,
            "The deposit must remain visible in the Open Items report",
        )
