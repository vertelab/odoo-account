from odoo import api, fields, models, _
from odoo.exceptions import ValidationError



class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"
    
    notice_period_note = fields.Text(string='Description on the Invoice for notice period', translate=True)
