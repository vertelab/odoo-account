from odoo import models, fields, api

class AccountBalanceRecord(models.Model):
    _name = 'account.balance'
    _inherit = ["mis.budget.abstract"]
    _description = 'Account Balance'

    fiscalyear_id = fields.Many2one('account.fiscalyear', string='Fiscal Year', required=True, ondelete='cascade')
    account_id = fields.Many2one('account.account', string='Account', required=True)
    debit = fields.Monetary(string='Total Debit', currency_field='currency_id', default=0.0)
    credit = fields.Monetary(string='Total Credit', currency_field='currency_id', default=0.0)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id
    )
    date = fields.Date(string='Date', required=True)