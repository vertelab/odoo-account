import logging
from odoo import api, fields, models, _, exceptions
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
import traceback

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _set_period_domain(self):
        return [('state', '!=', 'done'), ('company_id', '=', self.env.company.id)]

    @api.depends("date")
    def _compute_period(self):
        for rec in self:
            if rec.date:
                period_ids = self.env['account.period'].date2period(rec.date)
                if len(period_ids) > 1:
                    _logger.warning("Multiple periods found for date %s: %s", rec.date, period_ids.ids)
                rec.period_id = period_ids[:1].id
            else:
                rec.period_id = False
    
    @api.model
    def _search_period_id(self, operator, value):
        if not value:
            return []

        # Normalize value to a list of IDs
        if isinstance(value, models.BaseModel):
            period_ids = value.ids
        elif isinstance(value, int):
            period_ids = [value]
        else:
            period_ids = list(value)

        if not period_ids:
            return [('id', '=', False)]

        periods = self.env['account.period'].browse(period_ids).exists()

        if not periods:
            return [('id', '=', False)]

        if len(periods) == 1:
            period = periods[0]
            if operator in ('!=', 'not in'):
                return ['|',
                    ('date', '<', period.date_start),
                    ('date', '>', period.date_stop),
                ]
            return [
                ('date', '>=', period.date_start),
                ('date', '<=', period.date_stop),
            ]

        # Multiple periods — build: OR of (date >= start AND date <= stop) for each
        # Domain: ['|', '|', ..., '&', c1, c2, '&', c1, c2, ...]
        # Number of '|' needed = len(periods) - 1
        domain = []

        if operator in ('!=', 'not in'):
            # NOT in any period range: AND of (date < start OR date > stop)
            for period in periods:
                domain += ['&',
                    ('date', '<', period.date_start),
                    ('date', '>', period.date_stop),
                ]
            # Wrap with AND operators
            ands = ['&'] * (len(periods) - 1)
            return ands + domain
        else:
            for period in periods:
                domain += ['&',
                    ('date', '>=', period.date_start),
                    ('date', '<=', period.date_stop),
                ]
            ors = ['|'] * (len(periods) - 1)
            return ors + domain

    period_id = fields.Many2one(
        comodel_name='account.period',
        string='Period',
        domain=_set_period_domain,
        compute=_compute_period,
        search=_search_period_id,
        compute_sudo = True
    )

    payment_period_id = fields.Many2one(
        store=True, comodel_name='account.period', string='Payment Invoice Period',
        compute="_set_period_from_payment", readonly=True
    )
    payment_date = fields.Date(
        store=True, string='Invoice Payment Date', compute="_set_date_from_payment", readonly=True
    )
    payment_move_id = fields.Many2one(
        store=True, comodel_name='account.move', string='The payment invoice',
        compute="_set_payment_invoice", readonly=True
    )

    @api.depends("payment_move_id.period_id", "payment_move_id")
    def _set_period_from_payment(self):
        for rec in self:
            if rec.payment_move_id:
                rec.payment_period_id = rec.payment_move_id.period_id
            else:
                rec.payment_period_id = False

    @api.depends("payment_move_id.date", "payment_move_id")
    def _set_date_from_payment(self):
        for rec in self:
            if rec.payment_move_id:
                rec.payment_date = rec.payment_move_id.date
            else:
                rec.payment_date = False

    @api.depends("payment_state", "state")
    def _set_payment_invoice(self):
        for rec in self:
            rec.payment_move_id = False
            return

        for rec in self:
            if rec.state == 'posted' and rec.is_invoice(include_receipts=True) and rec.payment_state == 'paid':
                # Used when searching for account_moves using the cash method with mis_builder. Currently it's
                # linking the latest payment account.move so that the mis_instance can search using its period or
                # date. I'm not sure how to handle multiple payments which is why im only linking the latest one.

                rec._compute_payments_widget_reconciled_info()
                list_of_payments = rec.invoice_payments_widget
                if list_of_payments:
                    latest_payment = self.env['account.move'].search([('id', '=', list_of_payments[0]['move_id'])],
                                                                     limit=1)
                    for payment in list_of_payments:
                        current_payment = self.env['account.move'].search([('id', '=', payment['move_id'])], limit=1)
                        if current_payment.period_id.date_stop > latest_payment.period_id.date_stop:
                            latest_payment = current_payment
                        rec.payment_move_id = latest_payment
                else:
                    rec.payment_move_id = False
            else:
                rec.payment_move_id = False

    def action_post(self):
        _logger.warning(f"Context is: {self.env.context}")
        context = self.env.context

        # period_by_journal = self.env['account.period']._get_period_by_journal(
        #     self.journal_id, self.date
        # )
        for record in self:
            if self.period_id and self.period_id.state == 'done' and (context.get("default_move_type", False) or context.get("display_account_trust", False)):
                _logger.error("Ett undantag inträffade:\n%s", traceback.format_exc())
                raise ValidationError(_(
                    "You have tried to validate an invoice on a closed period {self.period_id.name}.\n Please change "
                    "period or open {self.period_id.name}").format(**locals())
                )

        # if period_by_journal:
        #     raise ValidationError(_(
        #         "You have tried to validate an invoice that has the journal closed {self.journal_id.name}.\n Please change "
        #         "journal or remove it from the period {self.period_id.name}").format(**locals())
        #     )
        return super(AccountMove, self).action_post()

    @api.depends('period_id', 'date')
    def compute_period_date(self):
        for record in self:
            if record.period_id and record.date:
                if record.date > record.period_id.date_stop or record.date < record.period_id.date_start:
                    record.invoicing_date_warning = True
                else:
                    record.invoicing_date_warning = False
            else:
                record.invoicing_date_warning = False

    invoicing_date_warning = fields.Boolean(string='A warning', compute=compute_period_date)

