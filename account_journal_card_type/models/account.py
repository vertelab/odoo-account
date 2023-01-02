# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2017 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import api, fields, models, _, exceptions
from odoo.osv import expression
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import Warning
from odoo.exceptions import ValidationError, UserError

import logging

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'
    type = fields.Selection(default="general",
                            selection_add=[("card", "Card")],
                            ondelete={"card": "set default"},
                            )

    card_debit_account = fields.Many2one('account.account', string='Card Debit Account')
    card_credit_account = fields.Many2one('account.account', string='Card Credit Account')
        # ~ domain="[('deprecated', '=', False), ('company_id', '=', company_id),"
               # ~ "'|', ('user_type_id', '=', default_account_type),"
               # ~ "('user_type_id.type', '=', 'other')]")
    

    def open_action_with_context_mynt(self):
        _logger.warning("{open_action_with_context_mynt}" * 10)
        action_name = self.env.context.get('action_name', False)
        if not action_name:
            return False
        ctx = dict(self.env.context, default_journal_id=self.id)
        _logger.warning(f"before {ctx=}")
        if ctx.get('search_default_journal', False):
            ctx.update(search_default_journal_id=self.id)
            ctx['search_default_journal'] = False  # otherwise it will do a useless groupby in bank statements
        ctx.pop('group_by', None)
        _logger.warning(f"after {ctx=}")
        action = self.env['ir.actions.act_window']._for_xml_id(f"account_journal_card_type.{action_name}")
        action['context'] = ctx
        if ctx.get('use_domain', False):
            action['domain'] = isinstance(ctx['use_domain'], list) and ctx['use_domain'] or ['|', (
                'journal_id', '=', self.id), ('journal_id', '=', False)]
            action['name'] = _(
                "%(action)s for journal %(journal)s",
                action=action["name"],
                journal=self.name,
            )
        return action


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _get_default_journal(self):
        """ Get the default journal.
        It could either be passed through the context using the 'default_journal_id' key containing its id,
        either be determined by the default type.
        """
        move_type = self._context.get('default_move_type', 'entry')
        if move_type in self.get_sale_types(include_receipts=True):
            journal_types = ['sale']
        elif move_type in self.get_purchase_types(include_receipts=True):
            journal_types = ['purchase']
        else:
            journal_types = self._context.get('default_move_journal_types', ['general'])

        if self._context.get('default_journal_id'):
            journal = self.env['account.journal'].browse(self._context['default_journal_id'])
            _logger.warning(f"{journal_types=}")
            journal_types.append('card')
            if move_type != 'entry' and journal.type not in journal_types:
                raise UserError(_(
                    "Cannot create an invoice of type %(move_type)s with a journal having %(journal_type)s as type.",
                    move_type=move_type,
                    journal_type=journal.type,
                ))
        else:
            journal = self._search_default_journal(journal_types)

        return journal

    @api.model
    def get_purchase_types(self, include_receipts=False):
        return ['in_invoice', 'in_refund'] + (include_receipts and ['in_receipt'] or [])

    @api.constrains('move_type', 'journal_id')
    def _check_journal_type(self):
        for record in self:
            journal_type = record.journal_id.type

            # if record.is_sale_document() and journal_type != 'sale' or record.is_purchase_document() and
            # journal_type != 'purchase':
            if record.is_sale_document() and journal_type not in ['sale', 'card'] or record.is_purchase_document() \
                    and journal_type not in ['purchase', 'card']:
                raise ValidationError(
                    _("The chosen journal has a type that is not compatible with your invoice type. Sales operations "
                      "should go to 'sale' journals, and purchase operations to 'purchase' ones."))
