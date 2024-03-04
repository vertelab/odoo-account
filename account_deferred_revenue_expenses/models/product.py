
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)



# https://stackoverflow.com/questions/356323/cant-add-all-files-to-git-due-to-permissions
class Product(models.Model):
    _inherit = "product.product"

    deferred_expense_profile_id = fields.Many2one("account.asset.profile", string="Deferred expense profile", help="Makes accounting more simple when using deferred template.")

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    @api.onchange('product_id')
    def _compute_deferred_expense(self):
        _logger.warning("_compute_deferred_expense"*100)
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue
            line.deferred_expense_profile_id= line.product_id.deferred_expense_profile_id.id
