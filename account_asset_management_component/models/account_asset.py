from odoo import models, fields, api, _


class AccountAsset(models.Model):
    _inherit = "account.asset"

    asset_parent_id = fields.Many2one('asset.parent', string="Parent")
