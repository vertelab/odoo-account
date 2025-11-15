
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_attachment_directory = fields.Char(
        string='Account Attachment Directory',
        config_parameter='account_attachment_directory',
        help="Path to a directory for loading attachements to Account Moves. "
    )
