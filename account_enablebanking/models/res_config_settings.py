from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_banking_api_url = fields.Char("API URL", config_parameter='enablebanking.api_url',
                                         related="company_id.enable_banking_api_url")
    enable_banking_application_id = fields.Char("Application ID", config_parameter='enablebanking.application_id',
                                                related="company_id.enable_banking_application_id")
    enable_banking_redirect_url = fields.Char("Redirect URL", config_parameter='enablebanking.redirect_url',
                                              related="company_id.enable_banking_redirect_url")
    enable_banking_private_key = fields.Text("Private Key", config_parameter='enablebanking.private_key',
                                             related="company_id.enable_banking_private_key")