import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class Product(models.Model):
    _inherit = "product.product"

    deferred_profile_id = fields.Many2one(
        "account.deferred.profile", string="Accrual Template",
        help="Default accrual profile when this product is used on an invoice line.",
    )
