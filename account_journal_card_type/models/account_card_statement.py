from odoo import api, fields, models, _
from odoo.exceptions import UserError


import logging
_logger = logging.getLogger(__name__)

class AccountCardStatement(models.Model):
    _name = 'account.card.statement'
    _inherit = ['mail.thread']

    name = fields.Char()
    date = fields.Date()
    account_card_statement_line_ids = fields.One2many('account.card.statement.line', 'account_card_statement_id', string='Card Transaction')
    account_move_id = fields.Many2one('account.move', string='Entry')
    journal_id = fields.Many2one('account.journal', string='Journal')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled'),
    ], string='Status', copy=False, index=True, track_visibility='onchange', default='draft')

    @api.model
    def create(self, vals):
        _rec_id = self.env[self._name].search([('name', '=', vals.get('name')), ('state', '!=', 'cancelled')], limit=1)
        if _rec_id:
            raise UserError(_('Bank Statement for this month already exists. You can cancel previous statement and create new one.'))
        return super(AccountCardStatement, self).create(vals)
    
    def button_journal_entries(self):
        return {
            'name': _('Journal Entries'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.account_card_statement_line_ids.account_move_id.ids)],
            'context': {
                'journal_id': self.journal_id.id,
            }
        }

    
    def unlink(self):
        for record in self:
            record.account_card_statement_line_ids.unlink()
        return super(AccountCardStatement, self).unlink()

    
    def action_post(self):
        if self.account_card_statement_line_ids:
            self.account_card_statement_line_ids.mapped('account_move_id').action_post()                 
            self.state = 'posted'

    def action_cancel(self):
        if self.account_card_statement_line_ids:
            move_ids = self.account_card_statement_line_ids.mapped('account_move_id').filtered(lambda move: move.state == 'posted')
            if move_ids:
                self._reverse_account_move(move_ids)
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

    account_card_statement_id = fields.Many2one('account.card.statement', string='Card Transaction', required=True, ondelete="cascade")
    account_move_id = fields.Many2one('account.move', string='Entry', required=True)
    date = fields.Date()
    amount = fields.Float()
    currency = fields.Many2one('res.currency', string='Currency')###res.currency
    original_amount = fields.Float()
    original_currency = fields.Char()
    vat_amount = fields.Float()
    vat_rate = fields.Char()
    reverse_vat = fields.Char()
    description	= fields.Char()
    account = fields.Many2one('account.account', string='Account')
    category = fields.Char()
    comment = fields.Text()
    filename = fields.Char()
    settlement_status = fields.Char()
    person = fields.Char()
    team = fields.Char()
    card_number	= fields.Char()
    card_name = fields.Char()
    accounting_status = fields.Char()

