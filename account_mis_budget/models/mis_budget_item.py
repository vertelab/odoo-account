
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MisBudgetByKPIItem(models.Model):
    _inherit = ['mis.budget.item', 'mail.thread', 'mail.activity.mixin']
    _name = "mis.budget.item"

    def action_read_budget_by_kpi(self):
        self.ensure_one()
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mis.budget.item',
            'res_id': self.id,
        }

