from odoo import models, fields, api, _


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    account_uuid = fields.Char(string="Account UUID")
    fintecture_customer_id = fields.Char(string="Fintecture Customer ID")
    fintecture_account_id = fields.Char(string="Fintecture Account ID")

    def action_create_account_journal(self):
        journal_id = self.env['account.journal'].search([
            ('code', '=', self.acc_number[:5])
        ], limit=1)
        if not journal_id:
            self.env['account.journal'].create({
                'name': self.acc_number[:5],
                'code': self.acc_number[:5],
                'type': 'bank',
                'bank_account_id': self.id,
                'currency_id': self.currency_id.id,
            })

