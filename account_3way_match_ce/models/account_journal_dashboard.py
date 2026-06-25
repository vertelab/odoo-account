from odoo import fields, models
from odoo.tools import SQL


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def open_action(self):
        action = super(AccountJournal, self).open_action()
        view = self.env.ref('account.action_move_in_invoice_type')
        if view and action.get("id") == view.id:
            action['context']['search_default_in_invoice'] = 0
            account_purchase_filter = self.env.ref('account_3way_match_ce.account_invoice_filter_inherit_account_3way_match', False)
            action['search_view_id'] = account_purchase_filter and [account_purchase_filter.id, account_purchase_filter.name] or False
        return action

    def _get_to_pay_select(self):
        return SQL("release_to_pay IN ('yes', 'exception') AS to_pay")

    def _get_draft_sales_purchases_query(self):
        domain_sale = [
            ('journal_id', 'in', self.filtered(lambda j: j.type == 'sale').ids),
            ('move_type', 'in', self.env['account.move'].get_sale_types(include_receipts=True))
        ]
        domain_purchase = [
            ('journal_id', 'in', self.filtered(lambda j: j.type == 'purchase').ids),
            ('move_type', 'in', self.env['account.move'].get_purchase_types(include_receipts=False)),
            '|',
            ('invoice_date_due', '<', fields.Date.today()),
            ('release_to_pay', '=', 'yes')
        ]
        domain = [
            ('state', '=', 'draft'),
            ('payment_state', 'in', ('not_paid', 'partial')),
        ]
        domain += self.env['account.move']._check_company_domain(self.env.companies)
        domain += ['|'] + domain_sale + domain_purchase
        return self.env['account.move']._search(domain, bypass_access=True)
