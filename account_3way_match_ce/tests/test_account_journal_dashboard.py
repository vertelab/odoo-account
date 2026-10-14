from freezegun import freeze_time

from odoo.addons.account.tests.test_account_journal_dashboard_common import TestAccountJournalDashboardCommon

from odoo.tests import tagged
from odoo.tools.misc import format_amount


@tagged('post_install', '-at_install')
class AccountJournalDashboard3WayMatchTest(TestAccountJournalDashboardCommon):
    """Dashboard-beteende som drivs av release_to_pay.

    Täcker de 3-way-specifika fallen: utkast-fakturor räknas som "att
    validera" när de är förfallna eller frigivna (release_to_pay = yes),
    och "att betala" räknar release_to_pay i (yes, exception).
    """

    @classmethod
    def init_invoice(cls, move_type, partner=None, invoice_date=None, post=False,
                     products=None, amounts=None, taxes=None, company=False,
                     currency=None, journal=None, invoice_date_due=None,
                     release_to_pay=None):
        move = super().init_invoice(move_type, partner, invoice_date, False,
                                    products, amounts, taxes, company, currency, journal)
        if invoice_date_due:
            move.invoice_date_due = invoice_date_due
        if release_to_pay:
            move.release_to_pay = release_to_pay
        if post:
            move.action_post()
        return move

    @freeze_time("2023-03-15")
    def test_purchase_journal_numbers_and_sums_to_validate(self):
        """Utkast-fakturor räknas som att validera när de är förfallna eller frigivna.

        Sex utkast-fakturor, alla med förfallodatum: tre förfallna
        (2023-03-01) och tre framtida (2023-04-30). Av de förfallna är en
        frigiven (yes) och en spärrad (no). Förväntat: fyra räknas som
        "att validera" — de tre förfallna (oavsett release_to_pay) plus den
        framtida som är frigiven.
        """
        company_currency = self.company_data['currency']
        journal = self.company_data['default_journal_purchase']

        datas = [
            {'invoice_date_due': '2023-04-30'},
            {'invoice_date_due': '2023-04-30', 'release_to_pay': 'yes'},
            {'invoice_date_due': '2023-04-30', 'release_to_pay': 'no'},
            {'invoice_date_due': '2023-03-01'},
            {'invoice_date_due': '2023-03-01', 'release_to_pay': 'yes'},
            {'invoice_date_due': '2023-03-01', 'release_to_pay': 'no'},
        ]

        for data in datas:
            self.init_invoice('in_invoice', invoice_date='2023-03-01', post=False,
                              amounts=[4000], invoice_date_due=data['invoice_date_due'],
                              release_to_pay=data.get('release_to_pay'))

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(4, dashboard_data['number_draft'])
        self.assertEqual(format_amount(self.env, 16000, company_currency), dashboard_data['sum_draft'])

    @freeze_time("2023-03-15")
    def test_purchase_journal_numbers_and_sums(self):
        """Postade fakturor räknas som "att betala" oavsett release_to_pay.

        Bas-klassen skapar tre postade fakturor (4000, 400, 40) med
        betalningsvillkor. Alla tre är "waiting", en är "late". Med
        release_to_pay-satt till exception på alla ska de fortfarande
        räknas (exception ingår i "att betala").
        """
        company_currency = self.company_data['currency']
        journal = self.company_data['default_journal_purchase']

        self._create_test_vendor_bills(journal)

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(3, dashboard_data['number_waiting'])
        self.assertEqual(format_amount(self.env, 4440, company_currency), dashboard_data['sum_waiting'])
        self.assertEqual(1, dashboard_data['number_late'])
        self.assertEqual(format_amount(self.env, 40, company_currency), dashboard_data['sum_late'])
