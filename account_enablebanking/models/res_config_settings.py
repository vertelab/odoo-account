from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_banking_api_url = fields.Char("API URL", config_parameter='enablebanking.api_url',
                                         related="partner_id.enable_banking_api_url")
    enable_banking_application_id = fields.Char("Application ID", config_parameter='enablebanking.application_id',
                                                related="partner_id.enable_banking_application_id")
    enable_banking_redirect_url = fields.Char("Redirect URL", config_parameter='enablebanking.redirect_url',
                                              related="partner_id.enable_banking_redirect_url")
    enable_banking_private_key = fields.Char("Private Key", config_parameter='enablebanking.private_key',
                                             compute='_compute_private_key')

    interval_number = fields.Integer(string="Interval Number", config_parameter='enablebanking.interval_number')

    interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')], string="Interval Type", config_parameter='enablebanking.interval_type')

    @api.depends('partner_id')
    def _compute_private_key(self):
        for rec in self:
            rec.enable_banking_private_key = rec.partner_id.enable_banking_private_key

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env.ref('account_enablebanking.enable_banking_transaction_sync').write({
            'interval_number': self.interval_number,
            'interval_type': self.interval_type
        })