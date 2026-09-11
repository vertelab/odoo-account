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
    """The partner drill-down must list the invoices behind the balance for the
    report date, and must never list bank/payment entries (T/11301, T/11336).
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

        This is the kind of unreconciled ``entry`` line that must never show up
        as an "invoice" in the drill-down.
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

    def _drilldown_move_ids(self, partner, date_at):
        """Run the report and return the partner's clickable move ids."""
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
        res = self.report._get_report_values(wizard.ids, data)
        for account in res.get("aged_partner_balance", []):
            for row in account.get("partners", []):
                if row.get("id") == partner.id:
                    return row.get("move_ids")
        return None

    # ------------------------------------------------------------------- tests

    def test_open_invoice_listed_and_deposit_excluded(self):
        """An open invoice is listed; an open bank/deposit entry is not."""
        today = fields.Date.context_today(self.env.user)
        partner = self._new_partner("Drilldown Open Invoice")
        invoice = self._post_invoice(
            partner, 1000.0, today - timedelta(days=10), today - timedelta(days=5)
        )
        self._post_deposit(partner, 500.0, today - timedelta(days=3))

        move_ids = self._drilldown_move_ids(partner, today)

        self.assertEqual(
            move_ids,
            [invoice.id],
            "Only the open invoice should be listed, not the deposit entry",
        )

    def test_backdated_lists_invoice_paid_after_report_date(self):
        """A backdated run lists an invoice that was open then but is paid now."""
        today = fields.Date.context_today(self.env.user)
        report_date = today - timedelta(days=30)
        partner = self._new_partner("Drilldown Backdated")
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

        self.assertEqual(
            self._drilldown_move_ids(partner, report_date),
            [invoice.id],
            "A paid-after-report-date invoice must still be listed when backdating",
        )
        # Fully settled today -> the invoice is not part of the balance, so the
        # partner has no clickable invoice list at all (no row / empty list).
        self.assertFalse(
            self._drilldown_move_ids(partner, today),
            "The settled invoice is no longer open today, so it is not listed",
        )

    def test_deposit_only_partner_gets_empty_list(self):
        """A partner whose balance is only deposits gets no invoice list."""
        today = fields.Date.context_today(self.env.user)
        partner = self._new_partner("Drilldown Deposit Only")
        self._post_deposit(partner, 750.0, today - timedelta(days=2))

        move_ids = self._drilldown_move_ids(partner, today)

        self.assertEqual(
            move_ids,
            [],
            "Bank/deposit entries must never be listed as invoices",
        )
