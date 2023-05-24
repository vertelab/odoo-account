from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    contact_id = fields.Many2one('res.partner', string='Contact')

    # This method is intended to be used by a manual server action, to set the
    #  contact on all invoices correctly, on modul removal and instilation.
    def update_contact_name(self):
        for move in self:
            if move.invoice_origin:
                order_name = move.invoice_origin.split(',')[0]
                order = move.env['sale.order'].search([('name','=',order_name)])
                if order:
                    move.contact_id = order.partner_id.id
