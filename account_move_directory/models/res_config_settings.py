
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_move_directory = fields.Char(
        string='Account Move Directory',
        config_parameter='account_move_directory',
        help="Path to a directory for loading Account Moves. "
    )
