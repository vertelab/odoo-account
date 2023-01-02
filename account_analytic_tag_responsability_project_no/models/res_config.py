from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    hard_invoice_account_check = fields.Boolean(string='Harsh Analytic Tag Enforcement', help="Harsh Analytic Tag Enforcement: Disable this if some function in odoo keeps complaining about a missing  project or Cost Center tag", config_parameter='account_analytic_tag_responsability_project_no.hard_invoice_account_check', default=False)

        




