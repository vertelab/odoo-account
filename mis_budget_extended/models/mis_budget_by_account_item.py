
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MisBudgetByAccountItem(models.Model):
    _inherit = ['mis.budget.by.account.item', 'mail.thread', 'mail.activity.mixin']
    _name = "mis.budget.by.account.item"

    def action_read_budget_by_account(self):
        self.ensure_one()
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mis.budget.by.account.item',
            'res_id': self.id,
        }

