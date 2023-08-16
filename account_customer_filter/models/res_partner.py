from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    
    @api.depends('invoice_ids','invoice_ids.state')
    def set_has_confirmed_customer_invoices(self):
       _logger.warning("set_has_confirmed_customer_invoices"*100)
       _logger.warning(f"{self=}")
       for record in self:
           _logger.warning(f"{record.invoice_ids=}")
           record.has_confirmed_customer_invoices = len(record.invoice_ids.filtered(lambda invoice: invoice.state == 'posted' and invoice.move_type in ['out_invoice','out_refund'])) > 0
           

    has_confirmed_customer_invoices = fields.Boolean(compute=set_has_confirmed_customer_invoices, store=True)
    
    # ~ def set_all_old_customers(self):
        # ~ _logger.warning("set_all_old_customers"*100)
        # ~ all_contacts = self.env['res.partner']
        # ~ _logger.warning(f"{all_contacts=}")
        # ~ all_contacts.set_has_confirmed_customer_invoices()

