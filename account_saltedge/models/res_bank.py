from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


# class SaltedgeEstablishedSessions(models.Model):

#     _name = "saltedge.connection.id"
#     saltedge_connection_id = fields.Char("Established Session ID")


class ResBank(models.Model):
    
    _inherit = "res.bank"

#    saltedge_connection_ids = fields.One2many("saltedge.connection.id", "saltedge_connection_id", "Established Session IDs")
    api_contact_integration = fields.Many2one("res.partner", string="API Contact Integration")
    saltedge_connection_id = fields.Char("Established Session ID")

    def action_authorize_bank(self):
        
        if not self.country:
            raise ValidationError("Set a country for the bank")
        if not self.api_contact_integration:
            raise ValidationError("Set a API Contact Integration for the bank")
        
        partner_id = self.api_contact_integration
        
        auth_data = partner_id.action_sync_transactions_with_saltedge(self)

        redirect_url = auth_data.get("redirect_url") 

        if redirect_url:
            return {
                'type': 'ir.actions.act_url',
                'url': redirect_url,
                'target': 'self'
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': auth_data.get('error'),
                    'message': auth_data.get('message'),
                    'sticky': False,
                }
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

