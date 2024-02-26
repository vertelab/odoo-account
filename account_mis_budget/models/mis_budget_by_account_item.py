
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

    @api.depends("date_from", "date_to")
    def _compute_actual_amount(self):
        for rec in self:
            if (rec.date_from or rec.date_to) and rec.account_id:
                count, actual_amount = self._get_account_amount(rec.account_id, rec.date_from, rec.date_to)
                rec.actual_amount = actual_amount
                rec.account_move_line_count = count
            else:
                rec.actual_amount = 0
                rec.account_move_line_count = 0

    def _get_account_amount(self, account_id, date_from, date_to):
        move_line_ids = self.env['account.move.line'].search([
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('account_id', '=', account_id.id),
            ('move_id.state', '=', 'posted'),
        ])
        return len(move_line_ids), sum(move_line_ids.mapped('balance'))

    actual_amount = fields.Float(string="Actual Amount", compute=_compute_actual_amount)
    account_move_line_count = fields.Float(string="Move Line Count", compute=_compute_actual_amount)

    def action_view_account_item(self):
        self.ensure_one()
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'tree',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'domain': [
                ('account_id', '=', self.account_id.id),
                ('date', '>=', self.date_from), ('date', '<=', self.date_to)
            ]
        }


