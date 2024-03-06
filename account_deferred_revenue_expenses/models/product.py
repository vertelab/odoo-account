
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)



# https://stackoverflow.com/questions/356323/cant-add-all-files-to-git-due-to-permissions
class Product(models.Model):
    _inherit = "product.product"

    deferred_expense_profile_id = fields.Many2one("account.asset.profile", string="Accrual Template", help="Makes accounting more simple when using deferred template.")

