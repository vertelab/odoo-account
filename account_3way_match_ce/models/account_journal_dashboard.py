"""Dashboard-integration för release-to-pay (Odoo 18.0).

Bokföringsjournalens dashboard visar leverantörsfakturor som "att betala"
och utkast-fakturor som "att validera". Med 3-vägsmatchning ska:

* endast fakturor frigivna för betalning (`release_to_pay` i `yes`/`exception`)
  räknas som "att betala";
* utkast-leverantörsfakturor räknas som "att validera" när de är förfallna
  eller frigivna.

Odoo 18 bygger dashboardens data ur SQL-queries. Hooks som måste överskridas:

* `_get_draft_sales_purchases_query()` — returnerar en `Query` (inte en
  recordset), som core sedan `.select(...)` på.
* `_get_open_sale_purchase_query(journal_type)` — returnerar `(query, selects)`
  där `selects` innehåller `to_pay`-uttrycket.
"""

from odoo import fields, models
from odoo.tools import SQL


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def open_action(self):
        """Öppna listan över leverantörsfakturor med 3-vägsfiltret förvalt."""
        action = super().open_action()
        purchase_action = self.env.ref('account.action_move_in_invoice_type', raise_if_not_found=False)
        if purchase_action and action.get('id') == purchase_action.id:
            action['context']['search_default_in_invoice'] = 0
            search_view = self.env.ref(
                'account_3way_match_ce.account_invoice_filter_inherit_account_3way_match',
                raise_if_not_found=False)
            action['search_view_id'] = search_view and [search_view.id, search_view.name] or False
        return action

    def _get_draft_sales_purchases_query(self):
        """Utkast-fakturor för dashboarden.

        Säljfakturor räknas som vanligt. Leverantörsfakturor räknas när de är
        förfallna eller frigivna för betalning (`release_to_pay = yes`).
        """
        today = fields.Date.context_today(self)
        return self.env['account.move']._where_calc([
            *self.env['account.move']._check_company_domain(self.env.companies),
            ('journal_id', 'in', self.ids),
            ('state', '=', 'draft'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            '|',
            ('move_type', 'in', self.env['account.move'].get_sale_types(include_receipts=True)),
            '&',
            ('move_type', 'in', self.env['account.move'].get_purchase_types(include_receipts=False)),
            '|',
            ('invoice_date_due', '<', today),
            ('release_to_pay', '=', 'yes'),
        ])

    def _get_open_sale_purchase_query(self, journal_type):
        """Som core, men "att betala" styrs av release_to_pay.

        Leverantörsfakturor räknas som "att betala" endast när de är frigivna
        (`yes`/`exception`); säljfakturor räknas alltid.
        """
        query, selects = super()._get_open_sale_purchase_query(journal_type)
        if journal_type != 'purchase':
            return query, selects
        # Ersätt core:s `TRUE AS to_pay` med release_to_pay-filtret. Vi bygger
        # om listan och matchar på aliaset (sista ordet), inte på hela
        # strängen, så att core kan ändra uttrycket utan att filtret tystnar.
        return query, [
            SQL("release_to_pay IN ('yes', 'exception') AS to_pay")
            if select.code.strip().endswith('AS to_pay')
            else select
            for select in selects
        ]
