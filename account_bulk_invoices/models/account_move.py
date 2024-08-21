from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"

    partner_ids = fields.Many2many("res.partner", string="Customers")

    def invoice_vals(self):
        vals = {
            'move_type': 'out_invoice',
            'invoice_line_ids': self.invoice_line_ids.ids,
            'journal_id': self.journal_id.id,
            'ref': self.ref,
            'date': self.date,
            'fiscal_position_id': self.fiscal_position_id.id,
            'company_id': self.company_id.id,
            'invoice_user_id': self.invoice_user_id.id,
            'auto_post': self.auto_post,
            'to_check': self.to_check,
            'invoice_date_due': self.invoice_date_due,
            'payment_reference': self.payment_reference,
            'invoice_payment_term_id': self.invoice_payment_term_id.id,
        }
        return vals

    def action_create_invoice(self):
        vals = self.invoice_vals()
        move_id = self.env['account.move'].create(vals)

        for partner_id in self.partner_ids:
            partner_move_id = move_id.copy({'partner_id': partner_id.id})
            self._cleanup(partner_move_id)
        self.unlink()
        move_id.unlink()

    def _cleanup(self, partner_move_id):
        mail_message_id = self.env['mail.message'].search([
            ('model', '=', 'account.move'),
            ('res_id', '=', partner_move_id.id),
            ('record_name', '=', False)
        ])
        mail_message_id.unlink()

