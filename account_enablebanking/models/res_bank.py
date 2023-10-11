from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResBank(models.Model):
    _inherit = "res.bank"

    def action_authorize_bank(self):
        if not self.country:
            raise ValidationError("Set a country for the bank")
        company_id = self.env.user.company_id
        auth_url = company_id.action_sync_transactions_with_enable_banking(self)
        return {
            'type': 'ir.actions.act_url',
            'url': auth_url.get("url"),
            'target': 'self'
        }


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    account_uuid = fields.Char(string="Account UUID")

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
                'currency_id': self.currency_id.id
            })

