from odoo import api, fields, models, _, exceptions
from odoo.osv import expression
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError, Warning

import logging

_logger = logging.getLogger(__name__)

FIELDS = ['move_type','name','partner_id','invoice_date','journal_id','invoice_line_ids','line_ids','company_id','state']

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _reverse_moves(self, default_values_list=None, cancel=False):
        ''' Reverse a recordset of account.move.
        If cancel parameter is true, the reconcilable or liquidity lines
        of each original move will be reconciled with its reverse's.

        :param default_values_list: A list of default values to consider per move.
                                    ('type' & 'reversed_entry_id' are computed in the method).
        :return:                    An account.move recordset, reverse of the current self.
        '''
        if not default_values_list:
            default_values_list = [{} for move in self]

        if cancel:
            lines = self.mapped('line_ids')
            # Avoid maximum recursion depth.
            if lines:
                lines.remove_move_reconcile()

        reverse_type_map = {
            'entry': 'entry',
            'out_invoice': 'out_refund',
            'out_refund': 'entry',
            'in_invoice': 'in_refund',
            'in_refund': 'entry',
            'out_receipt': 'entry',
            'in_receipt': 'entry',
        }

        move_vals_list = []
        for move, default_values in zip(self, default_values_list):
            default_values.update({
                'move_type': reverse_type_map[move.move_type],
                'reversed_entry_id': move.id,
            })
            move_vals_list.append(
                move.with_context(move_reverse_cancel=cancel)._reverse_move_vals(default_values, cancel=cancel)
            )
        ###############################
        for move_vals in move_vals_list:
            period_id = self.env['account.period'].date2period(move_vals['date'])
            move_vals['period_id'] = period_id.id
        ###############################
        reverse_moves = self.env['account.move'].create(move_vals_list)
        for move, reverse_move in zip(self, reverse_moves.with_context(check_move_validity=False)):
            # Update amount_currency if the date has changed.
            if move.date != reverse_move.date:
                for line in reverse_move.line_ids:
                    if line.currency_id:
                        line._onchange_currency()
            reverse_move._recompute_dynamic_lines(recompute_all_taxes=False)
        reverse_moves._check_balanced()

        # Reconcile moves together to cancel the previous one.
        if cancel:
            reverse_moves.with_context(move_reverse_cancel=cancel)._post(soft=False)
            for move, reverse_move in zip(self, reverse_moves):
                lines = move.line_ids.filtered(
                    lambda x: (x.account_id.reconcile or x.account_id.internal_type == 'liquidity')
                              and not x.reconciled
                )
                for line in lines:
                    counterpart_lines = reverse_move.line_ids.filtered(
                        lambda x: x.account_id == line.account_id
                                  and x.currency_id == line.currency_id
                                  and not x.reconciled
                    )
                    (line + counterpart_lines).with_context(move_reverse_cancel=cancel).reconcile()

        return reverse_moves

    def validate_open_period_create(self, values):
        period_id = self.env['account.period'].browse(values.get('period_id'))
        if period_id and period_id.state == 'done':
            raise ValidationError(
                _("You have tried to create an invoice on a closed period {period_id.name}.\n Please change period or "
                  "open {period_id.name}").format(
                    **locals()))

    def validate_open_period_write(self, values):
        period_id = self.env['account.period'].browse(values.get('period_id'))
        if period_id and period_id.state == 'done':
            raise ValidationError(
                _("You have tried to write to an invoice with a closed period {period_id.name}.\n Please change "
                  "period or open {period_id.name}").format(
                    **locals()))

    def write(self, values):
        if self._context.get('check_move_period_validity', True):
            for record in self:
                # ~ _logger.warn(f'{values=} {self._context=}')
                if not set(values.keys()).intersection(FIELDS): # Check only when a critical field are in values
                    continue
                record.validate_open_period_write({"period_id": record.period_id.id})
        return super(AccountMove, self).write(values)

    @api.model_create_multi
    def create(self, values):
        for v in values: # add period if missing
            if not 'period_id' in v:
                v['period_id'] = self.env['account.period'].date2period \
                    (v.get('date') or v.get('invoice_date') or fields.Date.today()).id

        if self._context.get('check_move_period_validity', True):
            if isinstance(values, list):
                for i in range(len(values)):
                    self.validate_open_period_create(values[i])
            else:
                self.validate_open_period_create(values)
        return super(AccountMove, self).create(values)


    def _get_default_period_id(self):
        return self.env['account.period'].date2period(self.invoice_date or fields.Date.today()).id

    def _set_period_domain(self):
        return [('state', '!=', 'done'), ('company_id', '=', self.env.company.id)]

    period_id = fields.Many2one(
        comodel_name='account.period', string='Period', default=_get_default_period_id,
        required=True, states={'posted': [('readonly', True)]}, domain=_set_period_domain)

    period_date_start = fields.Date(string='Start of Period', related='period_id.date_start', required=True, store=True)
    period_date_stop = fields.Date(string='End of Period', related='period_id.date_stop', required=True, store=True)

    payment_period_id = fields.Many2one(store=True, comodel_name='account.period', string='Payment Invoice Period',
                                        compute="_set_period_from_payment", readonly=True)
    payment_date = fields.Date(store=True, string='Invoice Payment Date', compute="_set_date_from_payment",
                               readonly=True)
    payment_move_id = fields.Many2one(store=True, comodel_name='account.move', string='The payment invoice',
                                      compute="_set_payment_invoice", readonly=True)

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
            if rec.state == 'posted' and rec.is_invoice(include_receipts=True) and rec.payment_state == 'paid':
                # Used when searching for account_moves using the cash method with mis_builder. Currently it's
                # linking the latest payment account.move so that the mis_instance can search using its period or
                # date. I'm not sure how to handle multiple payments which is why im only linking the latest one.
                list_of_payments = rec._get_reconciled_info_JSON_values()
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

    @api.onchange("date", "invoice_date")
    def set_period_based_on_date(self):
        if self.date:
            period_id = self.env['account.period'].date2period(self.date)
            if period_id and period_id.state == 'done':
                raise ValidationError(
                    _("You have tried to create an invoice on a closed period {period_id.name}.\n Please change "
                      "period or open {period_id.name}").format(
                        **locals()))
            elif period_id:
                self.period_id = period_id

    def action_post(self):
        if self.period_id and self.period_id.state == 'done':
            raise ValidationError(
                _("You have tried to validate an invoice on a closed period {self.period_id.name}.\n Please change "
                  "period or open {self.period_id.name}").format(
                    **locals()))
        return super(AccountMove, self).action_post()

    def compute_period_date(self):
        for record in self:
            if record.period_id.date_stop and \
                    (record.date > record.period_id.date_stop or record.date < record.period_id.date_start):
                record.invoicing_date_warning = True
            else:
                record.invoicing_date_warning = False

    invoicing_date_warning = fields.Boolean(string='A warning', compute=compute_period_date)

    @api.onchange('invoice_date', 'period_id', 'date')
    def toogle_invoicing_date_warning(self):
        self.compute_period_date()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    period_id = fields.Many2one(
        'account.period', string='Period', related='move_id.period_id', store=True, readonly=True
    )
    period_date_start = fields.Date(string='Start of Period', related='period_id.date_start', required=True, store=True)
    period_date_stop = fields.Date(string='End of Period', related='period_id.date_stop', required=True, store=True)
    fiscalyear_id = fields.Many2one(
        comodel_name='account.fiscalyear', related='period_id.fiscalyear_id', store=True, readonly=True
    )