from odoo import models, fields, api, _


class AccountAsset(models.Model):
    _inherit = "account.asset"

    hr_dept_id = fields.Many2one('hr.department', string="Department")
