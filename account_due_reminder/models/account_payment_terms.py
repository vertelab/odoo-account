from odoo import models, fields, api, _


class PaymentTerms(models.Model):
    _inherit = 'account.payment.term'

    payment_reminder_line_ids = fields.Many2many(
        'payment.reminder.line',
        'payment_term_reminder_rel',
        'payment_term_id',
        'reminder_line_id',
        string="Reminders"
    )