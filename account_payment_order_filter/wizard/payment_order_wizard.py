# © 2009 EduSense BV (<http://www.edusense.nl>)
# © 2011-2013 Therp BV (<https://therp.nl>)
# © 2014-2015 ACSONE SA/NV (<https://acsone.eu>)
# © 2015-2016 Akretion (<https://www.akretion.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models


class AccountPaymentLineCreate(models.TransientModel):
    _name = "account.payment.line.create"
    _description = "Wizard to create payment lines"
    
payment_mode_id = env['payment.payment.mode'].search([('name','=','SEPA Direct Debit of customers')])
for record in records:
    if record.type == "contact" and "@skf" not in record.email and payment_mode_id:
        record.write({'customer_payment_mode_id':payment_mode_id.id})
        
