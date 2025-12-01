from odoo import models, fields, api


class AccountAssetLine(models.Model):
    _inherit = 'account.asset.line'

    skip = fields.Boolean(string="Skip Line", help="Set this flag, if you dont want it recomputed.")

