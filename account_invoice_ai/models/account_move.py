from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError
import json

import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    ai_session_id = fields.Many2one(comodel_name='ai.quest.session', string="", help="")
    to_check_duplicate = fields.Boolean()
    to_check_period = fields.Boolean()

    def action_view_ai_session(self):
        view = self.env.ref('ai_agent.ai_quest_session_form')
        return {
            'name': _('AI Session'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ai.quest.session',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_id': self.ai_session_id.id
        }

    def _compute_purchase_auto_complete(self, move_id):
        if self.purchase_vendor_bill_id.vendor_bill_id:
            self.invoice_vendor_bill_id = self.purchase_vendor_bill_id.vendor_bill_id
            self._onchange_invoice_vendor_bill()
        elif self.purchase_vendor_bill_id.purchase_order_id:
            self.purchase_id = self.purchase_vendor_bill_id.purchase_order_id
        self.purchase_vendor_bill_id = False

        if not self.purchase_id:
            return
        context_copy = self.env.context.copy()
        context_copy.update({'check_move_validity':False})
        
        # Copy data from PO
        invoice_vals = self.purchase_id.with_company(self.purchase_id.company_id)._prepare_invoice()
        invoice_vals['currency_id'] = self.line_ids and self.currency_id or invoice_vals.get('currency_id')
        del invoice_vals['ref']
        self.update(invoice_vals)

        # Copy purchase lines.
        po_lines = self.purchase_id.order_line - self.line_ids.mapped('purchase_line_id')
        new_lines = self.env['account.move.line']
        sequence = max(self.line_ids.mapped('sequence')) + 1 if self.line_ids else 10
        account_id = self.env['account.account'].search([('code','=','4001')])
        for line in po_lines.filtered(lambda l: not l.display_type):
            line_vals = line._prepare_account_move_line(self)
            line_vals.update({
                'sequence': sequence,
                'account_id': account_id.id,
                'move_id': move_id
            })
            new_line = new_lines.with_context(context_copy).create(line_vals)
            sequence += 1
            new_line.account_id = new_line._get_computed_account()
            new_line._onchange_price_subtotal()

        #new_lines._onchange_mark_recompute_taxes()
        self.with_context(context_copy)._recompute_dynamic_lines()
        # Compute invoice_origin.
        origins = set(self.line_ids.mapped('purchase_line_id.order_id.name'))
        self.invoice_origin = ','.join(list(origins))

        # Compute ref.
        refs = self._get_invoice_reference()
        self.ref = ', '.join(refs)

        # Compute payment_reference.
        if len(refs) == 1:
            self.payment_reference = refs[0]
        

        self.purchase_id = False
        self._onchange_currency()

    def re_update_move_lines(self):
        self = self.sudo()
        context_copy = self.env.context.copy()
        context_copy.update({'check_move_period_validity': False})
        self = self.with_context(context_copy)
        if not self.ai_session_id:
            raise UserError(_("You don't have a valid session for this move"))
        if self.ai_session_id.invoice_metadata and self.ai_session_id:
            move_vals = eval(self.ai_session_id.invoice_metadata)
            _logger.info(f"{move_vals=}")
            if line_ids := move_vals.get('invoice_line_ids'):
                self.invoice_line_ids = line_ids

    def clear_move_lines(self):
        self.line_ids.unlink()
        
    def action_rerun(self):
        self = self.sudo()
        self.write({'line_ids': False})
        self.ai_session_id.ai_quest_id.mail(
            mail=self.ai_session_id.message_ids[-1], 
            session=self.ai_session_id
        )
