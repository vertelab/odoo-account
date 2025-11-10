from odoo import models, fields, api, _


class BulkAccountMove(models.TransientModel):
    _name = 'bulk.account.move.wizard'
    _description = 'Bulk Account Move Wizard'

    move_id = fields.Many2one('account.move', string='Invoice')
    partner_ids = fields.Many2many('res.partner', string='Partners')

    def action_create_bulk_invoice(self):
        for partner in self.partner_ids:
            self.move_id.copy({'partner_id': partner.id})