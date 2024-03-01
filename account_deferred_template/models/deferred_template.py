
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class DeferrerTemplatel(models.Model):
    _inherit = "account.move.form"

    deferrer_template_ids = fields.Many2one("account.move.form", string="Select template for deferred", help="Makes accounting more simple when using deferred template.")
  
