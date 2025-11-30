from odoo import models, fields, api, _
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    next_reminder_date = fields.Date('Next Reminder', compute='_compute_next_reminder', store=True)
    last_reminder_id = fields.Many2one('payment.reminder.line', 'Last Reminder Sent')
    reminder_count = fields.Integer('Reminders Sent', default=0)
    payment_plan_id = fields.Many2one('account.payment.plan', string='Payment Plan', copy=False)

    @api.depends('invoice_date_due', 'payment_state', 'invoice_payment_term_id', 'last_reminder_id')
    def _compute_next_reminder(self):
        today = fields.Date.today()
        for move in self:
            if move.payment_state in ('paid', 'in_payment') or not move.invoice_date_due:
                move.next_reminder_date = False
                continue

            # Get reminders from payment term
            reminders = move.invoice_payment_term_id.payment_reminder_line_ids.sorted('delay')
            if not reminders:
                move.next_reminder_date = False
                continue

            # Find next applicable reminder
            for reminder in reminders:
                reminder_date = move.invoice_date_due + timedelta(days=reminder.delay)
                if reminder_date > today and (
                        not move.last_reminder_id or reminder.delay > move.last_reminder_id.delay):
                    move.next_reminder_date = reminder_date
                    break
            else:
                move.next_reminder_date = False

    def _send_payment_reminder(self, reminder_line):
        """Send reminder for this invoice"""
        self.ensure_one()

        if reminder_line.send_email and reminder_line.mail_template_id:
            reminder_line.mail_template_id.send_mail(self.id, force_send=True)

        if reminder_line.send_sms and reminder_line.sms_template_id:
            reminder_line.sms_template_id._send(self.ids)

        if reminder_line.create_activity and reminder_line.activity_type_id:
            responsible = self._get_reminder_responsible(reminder_line)
            self.activity_schedule(
                activity_type_id=reminder_line.activity_type_id.id,
                summary=reminder_line.activity_summary or f"Payment reminder: {self.name}",
                note=reminder_line.activity_note,
                user_id=responsible.id
            )

        self.last_reminder_id = reminder_line
        self.reminder_count += 1
        self.message_post(body=f"Payment reminder sent: {reminder_line.name}")

    def _get_reminder_responsible(self, reminder_line):
        """Determine who should be assigned the activity"""
        self.ensure_one()

        responsible_type = reminder_line.activity_default_responsible_type

        # Salesperson from invoice
        if responsible_type == 'salesperson' and self.invoice_user_id:
            return self.invoice_user_id

        # Account manager from partner
        if responsible_type == 'account_manager' and self.partner_id.user_id:
            return self.partner_id.user_id

        # Fallback to invoice user or current user
        return self.invoice_user_id or self.env.user

    def action_send_reminders(self):
        """Manual action to send reminders"""
        for move in self:
            if move.payment_state in ('paid', 'in_payment'):
                continue

            reminders = move.invoice_payment_term_id.payment_reminder_line_ids
            for reminder in reminders.sorted('delay'):
                reminder_date = move.invoice_date_due + timedelta(days=reminder.delay)
                if fields.Date.today() >= reminder_date:
                    if not move.last_reminder_id or reminder.delay > move.last_reminder_id.delay:
                        move._send_payment_reminder(reminder)
                        break

    @api.model
    def _cron_send_payment_reminders(self):
        """Cron job to automatically send reminders"""
        today = fields.Date.today()

        # Find invoices that need reminders today
        invoices = self.search([
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('next_reminder_date', '=', today)
        ])

        for invoice in invoices:
            reminders = invoice.invoice_payment_term_id.payment_reminder_line_ids.filtered('auto_execute')
            for reminder in reminders.sorted('delay'):
                reminder_date = invoice.invoice_date_due + timedelta(days=reminder.delay)
                if reminder_date == today:
                    if not invoice.last_reminder_id or reminder.delay > invoice.last_reminder_id.delay:
                        try:
                            invoice._send_payment_reminder(reminder)
                        except Exception as e:
                            _logger.error(f"Failed to send reminder for {invoice.name}: {e}")
                        break

    def action_create_payment_plan(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.payment.plan",
            "context": {
                'default_account_move_id': self.id,
                'default_untaxed_amount': self.amount_untaxed,
            },
            "name": _("Payment Plan"),
            'view_mode': 'form',
            'view_id': self.env.ref('account_due_reminder.view_account_account_payment_plan_wizard_form').id,
            'target': 'new'
        }

    # def action_create_payment_plan(self):
    #     return {
    #         "type": "ir.actions.act_window",
    #         "res_model": "account.payment.plan",
    #         "domain": [('id', 'in', account_move_lines.move_id.ids)],
    #         "context": {"create": False, 'default_move_type': 'in_invoice'},
    #         "name": _("Vendor Bills"),
    #         'view_mode': 'list,form',
    #     }