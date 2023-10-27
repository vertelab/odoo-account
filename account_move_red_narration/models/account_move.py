from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    red_narration = fields.Text(string="Red Narration", help="Narration in this field is red in the pdf, It shows up before the regular narration field")
    

    @api.onchange('move_type')
    def _onchange_type_red_terms(self):
        ''' Onchange made to filter the partners depending of the type. '''
        if self.is_sale_document(include_receipts=True):
            if self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms'):
                self.red_narration = self.company_id.red_invoice_terms or self.env.company.red_invoice_terms
