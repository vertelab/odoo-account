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

    def _compute_purchase_auto_complete(self):
        if self.purchase_vendor_bill_id.vendor_bill_id:
            self.invoice_vendor_bill_id = self.purchase_vendor_bill_id.vendor_bill_id
            self._onchange_invoice_vendor_bill()
        elif self.purchase_vendor_bill_id.purchase_order_id:
            self.purchase_id = self.purchase_vendor_bill_id.purchase_order_id
        self.purchase_vendor_bill_id = False

        if not self.purchase_id:
            return

        context_copy = self.env.context.copy()
        context_copy.update({'check_move_validity': False})

        # Copy data from PO
        invoice_vals = self.purchase_id.with_company(self.purchase_id.company_id)._prepare_invoice()

        has_invoice_lines = bool(
            self.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_note', 'line_section')))
        new_currency_id = self.currency_id if has_invoice_lines else invoice_vals.get('currency_id')
        del invoice_vals['ref'], invoice_vals['payment_reference']
        del invoice_vals['company_id']  # avoid recomputing the currency
        if self.move_type == invoice_vals['move_type']:
            del invoice_vals['move_type']  # no need to be updated if it's same value, to avoid recomputes
        self.update(invoice_vals)
        self.currency_id = new_currency_id

        # Copy purchase lines.
        po_lines = self.purchase_id.order_line - self.invoice_line_ids.mapped('purchase_line_id')

        for invoice_line in self.invoice_line_ids:
            invoice_line.account_id = self.env['account.account'].search([('code', '=', '4001')], limit=1).id

        self._add_purchase_order_lines(po_lines)

        # Compute invoice_origin.
        origins = set(self.invoice_line_ids.mapped('purchase_line_id.order_id.name'))
        self.invoice_origin = ','.join(list(origins))

        # Compute ref.
        refs = self._get_invoice_reference()
        self.ref = ', '.join(refs)

        # Compute payment_reference.
        if not self.payment_reference:
            if len(refs) == 1:
                self.payment_reference = refs[0]
            elif len(refs) > 1:
                self.payment_reference = refs[-1]

        # Copy company_id (only changes if the id is of a child company (branch))
        if self.company_id != self.purchase_id.company_id:
            self.company_id = self.purchase_id.company_id

        self.purchase_id = False

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
