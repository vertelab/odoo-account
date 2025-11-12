from odoo import api, fields, models, _
from datetime import timedelta

class PaymentReminderLine(models.Model):
    _name = 'payment.reminder.line'
    _description = 'Payment Reminders'
    _order = 'delay asc'
    _check_company_auto = True

    name = fields.Char('Description', required=True, translate=True)
    delay = fields.Integer('Due Days', required=True,
                           help="The number of days after the due date of the invoice to wait before sending the reminder. "
                                "Can be negative if you want to send the reminder before the invoice due date.")
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    payment_term_ids = fields.Many2many(
        'account.payment.term',
        'payment_term_reminder_rel',
        'reminder_line_id',
        'payment_term_id',
        string="Used in Payment Terms"
    )

    mail_template_id = fields.Many2one(comodel_name='mail.template', domain="[('model', '=', 'account.move')]")
    send_email = fields.Boolean('Send Email', default=True)
    attach_invoices = fields.Boolean(string="Attach Invoices", default=True)
    additional_follower_ids = fields.Many2many(
        'res.users',
        'reminder_follower_rel',
        'reminder_id',
        'user_id',
        string="Add followers",
        help="If set, those users will be added as followers on the invoice."
    )

    sms_template_id = fields.Many2one(comodel_name='sms.template', domain="[('model', '=', 'account.move')]")
    send_sms = fields.Boolean('Send SMS Message')

    create_activity = fields.Boolean(string='Schedule Activity')
    activity_summary = fields.Char(string='Summary')
    activity_note = fields.Text(string='Note')
    activity_type_id = fields.Many2one(comodel_name='mail.activity.type', string='Activity Type', default=False)
    activity_default_responsible_type = fields.Selection(
        [('salesperson', 'Salesperson'), ('account_manager', 'Account Manager')],
        string='Responsible', default='salesperson',
        help="Determine who will be assigned to the activity:\n"
             "- Salesperson: Sales Person defined on the invoice\n"
             "- Account Manager: Sales Person defined on the customer")

    auto_execute = fields.Boolean(string="Automatic", default=True)

    _sql_constraints = [
        ('days_uniq', 'unique(company_id, delay)', 'Days of the follow-up lines must be different per company'),
        ('uniq_name', 'unique(company_id, name)',
         'A follow-up action name must be unique. This name is already set to another action.'),
    ]

    @api.onchange('auto_execute')
    def _onchange_auto_execute(self):
        if self.auto_execute:
            self.create_activity = False

    def _get_next_date(self):
        """Computes the next reminder date"""
        self.ensure_one()
        next_followup = self._get_next_followup()
        if next_followup:
            delay = next_followup.delay - self.delay
        else:
            previous_followup = self._get_previous_followup()
            if previous_followup:
                delay = self.delay - previous_followup.delay
            else:
                delay = self.delay
        return fields.Date.context_today(self) + timedelta(days=delay)

    def _get_next_followup(self):
        self.ensure_one()
        return self.env['payment.reminder.line'].search(
            [('delay', '>', self.delay), ('company_id', '=', self.env.company.id)],
            order="delay asc", limit=1)

    def _get_previous_followup(self):
        self.ensure_one()
        return self.env['payment.reminder.line'].search(
            [('delay', '<', self.delay), ('company_id', '=', self.env.company.id)],
            order="delay desc", limit=1)