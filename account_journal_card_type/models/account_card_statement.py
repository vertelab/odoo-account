from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class AccountCardStatement(models.Model):
    _name = 'account.card.statement'
    _description = 'Account Card Statement'
    _inherit = ['mail.thread']

    name = fields.Char()
    date = fields.Date()
    statement_line_credit_repayment_id = fields.Many2one('account.card.statement.line',
                                                         string='Credit Repayment Transaction')
    statement_line_credit_repayment_line_ids = fields.One2many('account.card.statement.line',
                                                               'repayment_account_card_statement_id',
                                                               string='Credit Repayment Transaction Line')
    account_move_id = fields.Many2one('account.move', string='Entry')
    total_card_transaction = fields.Float(compute="compute_total_card_transaction", string="Total Card Transactions",
                                          store=True)
    account_card_statement_line_ids = fields.One2many('account.card.statement.line', 'account_card_statement_id',
                                                      string='Card Transaction')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled'),
    ], string='Status', copy=False, index=True, tracking=True, default='draft')
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)

    @api.depends('account_card_statement_line_ids', 'account_card_statement_line_ids.amount')
    def compute_total_card_transaction(self):
        for record in self:
            total = 0
            for line in record.account_card_statement_line_ids:
                total += line.amount
            record.total_card_transaction = total

    @api.model
    def create(self, vals):
        _rec_id = self.env[self._name].search([('name', '=', vals.get('name')), ('state', '!=', 'cancelled'),
                                               ('journal_id', '=', vals.get('journal_id'))], limit=1)
        if _rec_id:
            raise UserError(
                _('Bank Statement for this month already exists. You can cancel previous statement and create new one.'))
        return super(AccountCardStatement, self).create(vals)

    def button_journal_entries(self):
        
        move_list = self.account_card_statement_line_ids.account_move_id.ids
        if self.statement_line_credit_repayment_id:
            move_list.append(self.statement_line_credit_repayment_id.account_move_id.id)

        return {
            'name': _('Journal Entries'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_list)],
            'context': {
                'journal_id': self.journal_id.id,
            }
        }

    def unlink(self):
        for record in self:
            record.account_card_statement_line_ids.unlink()
            record.statement_line_credit_repayment_id.unlink()
        return super(AccountCardStatement, self).unlink()

    def action_post(self):
        if self.account_card_statement_line_ids:
            self.account_card_statement_line_ids.mapped(
                'account_move_id').filtered(lambda move: move.line_ids).action_post()

        if self.statement_line_credit_repayment_line_ids:
            self.statement_line_credit_repayment_line_ids.mapped(
                'account_move_id').filtered(lambda move: move.line_ids).action_post()

        self.state = 'posted'

    def action_cancel(self):
        if self.account_card_statement_line_ids:
            move_ids = self.account_card_statement_line_ids.mapped('account_move_id').filtered(
                lambda move: move.state == 'posted')
            if move_ids:
                move_ids.button_draft()
    
            draft_move_ids = self.account_card_statement_line_ids.mapped('account_move_id').filtered(
                lambda move: move.state == 'draft')
            if draft_move_ids:
                for move_record in draft_move_ids:
                    move_record.button_cancel()

            self.state = 'cancelled'
            
        if self.statement_line_credit_repayment_id and self.statement_line_credit_repayment_id.account_move_id.state == 'posted':
            self.statement_line_credit_repayment_id.account_move_id.button_draft()
           
        if self.statement_line_credit_repayment_id and self.statement_line_credit_repayment_id.account_move_id.state == 'draft':
            self.statement_line_credit_repayment_id.account_move_id.button_cancel()
            self.state = 'cancelled'
            
    def _reverse_account_move(self, move_ids):
        reverse_id = self.env['account.move.reversal'].create({
            'move_ids': move_ids.ids,
            'refund_method': 'cancel',
            'date_mode': 'custom',
            'date': fields.Date.context_today(self),
        })
        reverse_id.reverse_moves()


class AccountCardStatementLine(models.Model):
    _name = 'account.card.statement.line'
    _description = 'Account Card Statement Line'

    name = fields.Char()
    account_card_statement_id = fields.Many2one('account.card.statement', string='Card Transaction', required=False,
                                                ondelete="cascade")
    repayment_account_card_statement_id = fields.Many2one('account.card.statement',
                                                          string='Card Transaction - RePayment', required=False,
                                                          ondelete="cascade")
    account_move_id = fields.Many2one('account.move', string='Entry', required=True)
    account_move_payment_state = fields.Selection(related='account_move_id.payment_state', string='Payment State')
    date = fields.Date()
    amount = fields.Float()
    currency = fields.Many2one('res.currency', string='Currency')  # res.currency
    original_amount = fields.Float()
    original_currency = fields.Char()
    vat_amount = fields.Float()
    vat_rate = fields.Char()
    reverse_vat = fields.Char()
    description = fields.Char()
    account = fields.Many2one('account.account', string='Account')
    category = fields.Char()
    comment = fields.Text()
    filename = fields.Char()
    settlement_status = fields.Char()
    person = fields.Char()
    team = fields.Char()
    card_number = fields.Char()
    card_name = fields.Char()
    accounting_status = fields.Char()
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
