from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = "account.move"

    important_invoice_narration = fields.Text(
        string="Red Narration",
        help="Narration in this field has larger text and is after the regular narration",
        compute="_compute_important_invoice_narration",
        store=True,
        readonly=False,  # set True if user should not edit it manually
    )

    @api.depends('move_type', 'company_id', 'company_id.important_invoice_narration')
    def _compute_important_invoice_narration(self):
        for move in self:
            # is_invoice() is available on account.move; otherwise check move_type
            if move.is_invoice():
                move.important_invoice_narration = move.company_id.important_invoice_narration
            else:
                move.important_invoice_narration = False
