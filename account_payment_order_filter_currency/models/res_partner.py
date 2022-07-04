from locale import currency
from odoo import _, api, fields, models
import logging
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    exclude_from_payment = fields.Boolean(string="Exclude From Payment")
    
    def write(self, values):
        res = super(ResPartner, self).write(values)
        _logger.warning(f"{self}")
        _logger.warning(f"{values}")
        if "exclude_from_payment" in values:
            for record in self:
                invoices = self.env['account.move'].search([('partner_id','=',record.id)])
                for invoice in invoices:
                    invoice.compute_exclude_payment_partner_and_move()
                
