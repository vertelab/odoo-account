from odoo import fields, models, api, _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    group_id = fields.Many2one("res.groups", string="Group")