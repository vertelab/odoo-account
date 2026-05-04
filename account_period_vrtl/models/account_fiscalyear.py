from datetime import datetime
from odoo import api, fields, models, _, exceptions
from odoo.osv import expression
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class AccountFiscalyear(models.Model):
    _name = 'account.fiscalyear'
    _description = 'Fiscal Year'
    _order = 'date_start, id'

    @api.model
    def default_date_start(self):
        return '%s-01-01' % fields.Date.today().strftime('%Y')

    @api.model
    def default_date_stop(self):
        return '%s-12-31' % fields.Date.today().strftime('%Y')

    name = fields.Char(string='Fiscal Year', required=True)
    code = fields.Char(string='Code', size=6, required=True)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    date_start = fields.Date(string='Start Date', default=default_date_start, required=True)
    date_stop = fields.Date(string='End Date', default=default_date_stop, required=True)
    
    period_ids = fields.One2many(comodel_name='account.period', inverse_name='fiscalyear_id', string='Periods')
    state = fields.Selection(
        [('draft', 'Open'), ('done', 'Closed')],
        string='Status',
        readonly=True,
        copy=False,
        default='draft'
    )
    

    outgoing_balance_record_ids = fields.One2many(
        'account.balance', 'fiscalyear_id', string='Outgoing Balance'
    )

    outgoing_balance_count = fields.Integer(string="Outgoing Balance Count", compute='_compute_outgoing_balance_count')

    @api.depends('outgoing_balance_record_ids')
    def _compute_outgoing_balance_count(self):
        for rec in self:
            if rec.outgoing_balance_record_ids:
                rec.outgoing_balance_count = len(rec.outgoing_balance_record_ids)
            else:
                rec.outgoing_balance_count = 0

    @api.constrains('date_start', 'date_stop')
    def _check_duration(self):
        for record in self:
            if record.date_start > record.date_stop:
                raise UserError('Error!\nThe start date of a fiscal year must precede its end date.')

    def _set_state(self):
        for record in self:
            state = "done"
            for period in record.period_ids:
                if period.state == "draft":
                    state = "draft"
                    break
            record.state = state

    def create_period3(self):
        return self.create_period(3)

    def create_period1(self):
        return self.create_period(1)

    def create_period(self, interval=1):
        for fy in self:

            ds = fy.date_start

            # Opening period
            self.env['account.period'].create({
                'name': "%s %s" % (_('Opening Period'), ds.strftime('%Y')),
                'code': ds.strftime('00/%Y'),
                'date_start': ds.strftime('%Y-%m-%d'),
                'date_stop': ds.strftime('%Y-%m-%d'),
                'special': True,
                'fiscalyear_id': fy.id,
                'company_id': fy.company_id.id,
                
            })

            # Regular periods
            while ds < fy.date_stop:
                de = ds + relativedelta(months=interval, days=-1)
                if de > fy.date_stop:
                    de = fy.date_stop

                self.env['account.period'].create({
                    'name': ds.strftime('%m/%Y'),
                    'code': ds.strftime('%m/%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'fiscalyear_id': fy.id,
                    'company_id': fy.company_id.id,
                    
                })
                ds = ds + relativedelta(months=interval)
        return True

    @api.model
    def find(self, dt=None, exception=True):
        res = self.finds(dt, exception)
        return res and res[0] or False

    @api.model
    def finds(self, dt=None, exception=True):
        if not dt:
            dt = fields.Date.context_today(self)
        args = [
            ('date_start', '<=', dt),
            ('date_stop', '>=', dt),
            ('company_id', '=', self.env.context.get('company_id', self.env.company.id))
        ]
        ids = self.env['account.fiscalyear'].search(args).mapped('id')
        if not ids:
            if exception:
                raise UserError(
                    _('There is no fiscal year defined for this date: %s.\n'
                      'Please go to Configuration/Periods and configure a fiscal year.') % dt
                )
            else:
                return []
        return ids

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=80):
        if args is None:
            args = []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('code', operator, name), ('name', operator, name)]
        else:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        ids = self.search(expression.AND([domain, args]), limit=limit)
        return [(record.id, record.name) for record in ids]

    def action_draft(self):
        for fiscalyear in self:
            fiscalyear.state = 'draft'
        return True

    def create_balance(self):
        for fy in self:
            # Find the previous fiscal year
            previous_fy = self.env['account.fiscalyear'].search(
                [
                    ('date_stop', '<', fy.date_start),
                    ('company_id', '=', fy.company_id.id)
                ],
                order='date_stop desc',
                limit=1
            )

            _logger.info(
                "Calculating balance for %s (Previous year: %s)",
                fy.name,
                previous_fy.name if previous_fy else 'None'
            )

            # Collect incoming balances from previous fiscal year (if any)
            incoming_balances = {}
            if previous_fy:
                for record in previous_fy.outgoing_balance_record_ids:
                    incoming_balances[record.account_id.id] = {
                        'debit': record.debit,
                        'credit': record.credit,
                    }

                if not incoming_balances:
                    _logger.info(
                        "Previous year %s has no balance records (starting from zero)", previous_fy.name
                    )

            # Get current fiscal year posted moves grouped by account
            current_moves = self.env['account.move.line'].read_group(
                domain=[
                    ('date', '>=', fy.date_start),
                    ('date', '<=', fy.date_stop),
                    ('move_id.state', '=', 'posted'),
                    ('company_id', '=', fy.company_id.id)
                ],
                fields=['account_id', 'debit:sum', 'credit:sum'],
                groupby=['account_id']
            )

            _logger.info("Found %d accounts with moves in %s", len(current_moves), fy.name)

            # Clear old records before recreating
            fy.outgoing_balance_record_ids.unlink()

            # Track which accounts have been processed
            accounts_processed = set()

            # Process accounts with current year moves
            for move_data in current_moves:
                account_id = move_data.get('account_id') and move_data['account_id'][0]
                if not account_id:
                    continue

                # Get incoming balances (0.0 if not found)
                inc_debit = incoming_balances.get(account_id, {}).get('debit', 0.0)
                inc_credit = incoming_balances.get(account_id, {}).get('credit', 0.0)

                # Calculate totals including incoming balances
                total_debit = inc_debit + move_data.get('debit', 0.0)
                total_credit = inc_credit + move_data.get('credit', 0.0)

                # Create new balance record
                self.env['account.balance'].create({
                    'fiscalyear_id': fy.id,
                    'account_id': account_id,
                    'debit': total_debit,
                    'credit': total_credit,
                    'date': self.date_stop
                })

                accounts_processed.add(account_id)

            # Handle accounts with only incoming balance but no current moves
            for acc_id, bal in incoming_balances.items():
                if acc_id not in accounts_processed:
                    self.env['account.balance'].create({
                        'fiscalyear_id': fy.id,
                        'account_id': acc_id,
                        'debit': bal['debit'],
                        'credit': bal['credit'],
                        'date': self.date_stop
                    })

            _logger.info(
                "Created %d balance records for fiscal year %s",
                len(fy.outgoing_balance_record_ids),
                fy.name
            )

            if fy.outgoing_balance_record_ids:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Created %d balance records for %s') % (len(fy.outgoing_balance_record_ids), fy.name),
                        'type': 'success',
                        'sticky': False,
                    }
                }

    def open_balances(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Outgoing Balances'),
            'res_model': 'account.balance',
            'domain': [('id', 'in', self.outgoing_balance_record_ids.ids)],
            'views': [[False, 'list'], [False, 'form']],
        }
