from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _


class AccountPaymentPlan(models.Model):
    _name = "account.payment.plan"
    _description = "Account Payment Plan"

    @api.depends('partner_id', 'account_move_id', 'start_date', 'duration')
    def _compute_name(self):
        for record in self:
            if record.partner_id and record.account_move_id:
                record.name = f"{record.partner_id.name} - {record.account_move_id.name} ({record.duration} months)"
            else:
                record.name = "New Payment Plan"


    name = fields.Char(string="Name", compute=_compute_name)
    account_move_id = fields.Many2one(
        "account.move", string="Account Move", readonly=True, index=True, copy=False, required=True)
    partner_id = fields.Many2one(related='account_move_id.partner_id', string="Partner", store=True)
    untaxed_amount = fields.Monetary(string="Untaxed Amount")
    tax_id = fields.Many2one("account.tax", string="Tax", required=True)
    currency_id = fields.Many2one(
        related='account_move_id.currency_id', string="Currency",  readonly=True
    )
    company_id = fields.Many2one(
        related='account_move_id.company_id', store=True, readonly=True
    )
    start_date = fields.Date(string="Payment Start Date", required=True, default=fields.Date.today)
    duration = fields.Integer(string="Payment Duration (Months)", compute='_compute_duration', readonly=True)
    end_date = fields.Date(string="Payment End Date", required=True)
    contract_id = fields.Many2one('contract.contract', string="Contract", copy=False)
    state = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], string="State", default='active')
    feared_loss_entry = fields.Many2one('account.move', string="Feared Loss")
    actual_loss_move = fields.Many2one('account.move', string="Actual Loss")

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.end_date >= record.start_date:
                    delta = relativedelta(record.end_date, record.start_date)
                    total_months = delta.years * 12 + delta.months
                    # If there are remaining days, count as an additional month
                    if delta.days > 0:
                        total_months += 1
                    record.duration = total_months if total_months > 0 else 1
                else:
                    record.duration = 0
            else:
                record.duration = 0

    def action_create_payment_plan(self):
        if not self.contract_id:
            contract_id = self.env['contract.contract'].create(self._contract_vals())
            name = f'{self.account_move_id.partner_id.name} - {self.account_move_id.name}'

            if self.account_move_id:
                self.account_move_id.payment_plan_id = self.id

            if contract_id:
                contract_id.write({
                    'date_end': self.end_date,
                    'contract_line_fixed_ids': [(0, 0, {
                        'name': name,
                        'quantity': 1,
                        'price_unit': self.untaxed_amount/self.duration,
                    })]
                })
                self.contract_id = contract_id.id
                # By default, the context will contain 'default_account_move_id'
                # from the invoice which is not correct.
                # We need to remove it from the context before creating stubs
                new_context = self.env.context.copy()
                new_context.pop('default_account_move_id', None)
                contract_id.with_context(new_context).compute_contract()
            self._write_off_entry()
        return self._view_contract()

    def _contract_vals(self):
        fiscal_position_id = self.env['account.fiscal.position']._get_fiscal_position(
            self.account_move_id.partner_id
        )
        name = f'{self.account_move_id.partner_id.name} - {self.account_move_id.name}'
        return {
            'name': name,
            'partner_id': self.account_move_id.partner_id.id,
            'date_start': self.start_date,
            'date_end': self.end_date,
            'fiscal_position_id': fiscal_position_id.id,
        }

    def _view_contract(self):
        name = f'{self.account_move_id.partner_id.name} - {self.account_move_id.name}'
        return {
            "type": "ir.actions.act_window",
            "res_model": "contract.contract",
            "name": _(f"{name} Contract"),
            'view_mode': 'form',
            'res_id': self.contract_id.id
        }

    def _get_account_code(self, code):
        return self.env['account.account'].search([('code', '=', code)], limit=1).id

    def _write_off_entry(self):
        _write_off_move_id = self.env['account.move'].sudo().with_context(check_move_validity=False).create({
            'move_type': 'entry',
            'journal_id': self.account_move_id.journal_id.id, # self.env.ref('account.1_general')
            'date': fields.Date.today(),
            'ref': self.account_move_id.name,
            'line_ids': self._write_off_lines(),
        })
        self.actual_loss_move = _write_off_move_id.id

        _write_off_move_id.action_post()

    def _write_off_lines(self):
        loss = self.account_move_id.amount_untaxed - self.untaxed_amount
        taxed_amount = (self.tax_id.amount / 100) * loss
        line_ids = [(0, 0, {
            'name': f'{self.name} - Untaxed',
            'account_id': self._get_account_code(6351),
            'debit': loss,
            #'debit': 0.0,
        }), (0, 0, {
            'name': f"{self.name} - Tax",
            'account_id': self._get_account_code(2610),
            'debit': taxed_amount,
            #'debit': taxed_amount,
        }), (0, 0, {
            'name': f"{self.name} - Receivable",
            'account_id': self._get_account_code(1510),
            #'credit': 0.0,
            'credit': loss + taxed_amount,
        })]

        return line_ids

    def action_mark_as_loss(self):
        self._loss_entry()
        self.state = 'inactive'

    def _loss_entry(self):
        _write_off_move_id = self.env['account.move'].sudo().with_context(check_move_validity=False).create({
            'move_type': 'entry',
            'journal_id': self.account_move_id.journal_id.id, # self.env.ref('account.1_general')
            'date': fields.Date.today(),
            'ref': self.move_id.name,
            'line_ids': self._write_off_lines(),
        })
        self.feared_loss_entry = _write_off_move_id.id

        _write_off_move_id.action_post()

    def _loss_entry_lines(self):
        # unpaid_amount = self._get_unpaid_amount()
        unpaid_amount = self.account_move_id.amount_untaxed - self.untaxed_amount


        line_ids = [(0, 0, {
            'name': f'{self.name} - Untaxed',
            'account_id': self._get_account_code(6352),
            'credit': 0.0,
            'debit': 0.0,
        }), (0, 0, {
            'name': f"{self.name} - Tax",
            'account_id': self._get_account_code(1519),
            'credit': 0.0,
            'debit': 0,
        })]

        return line_ids

    def _get_unpaid_amount(self):
        unpaid = self.contract_id.invoice_stub_ids.filtered(
            lambda line: not line.account_move_id or line.account_move_id.state != 'posted'
        )
        return sum(unpaid.mapped('amount'))