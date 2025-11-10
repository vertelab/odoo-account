from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_bulk_account_invoice(self):
        active_id = self.env.context.get('active_id', False)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bulk Account Invoice'),
            'view_mode': 'form',
            'res_model': 'bulk.account.move.wizard',
            'context': {'default_move_id': active_id},
            'target': 'new'
        }

