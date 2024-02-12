from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class ResBank(models.Model):
    _inherit = "res.bank"

    api_contact_integration = fields.Many2one("res.partner", string="API Contact Integration")
    provider_code = fields.Char(string="Fintecture Provider Code", help="A provider code that let the api know which bank to contact")

    def action_authorize_bank(self):
        if not self.country:
            raise ValidationError("Set a country for the bank")
        if not self.api_contact_integration:
            raise ValidationError("Set a API Contact Integration for the bank")
        if not self.provider_code:
            raise ValidationError("Set a provider code for the bank")
        
        partner_id = self.api_contact_integration
        
        provider_data = partner_id.get_provider_authorization(self)
        
        _logger.error(provider_data)

        if provider_data.get('url'):
            return {
                'type': 'ir.actions.act_url',
                'url': provider_data.get("url"),
                'target': 'self'
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': provider_data.get('error'),
                    'message': provider_data.get('message'),
                    'sticky': False,
                }
            }


