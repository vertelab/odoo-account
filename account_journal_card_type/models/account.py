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
from odoo.exceptions import ValidationError, UserError

import logging

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    type = fields.Selection(default="general",
                            selection_add=[("card", "Card")],
                            ondelete={"card": "set default"},
                            )

    card_debit_account = fields.Many2one('account.account', string='Card Debit Account',
                                           domain="[('deprecated', '=', False), ('company_ids', 'in', company_id)]")
                                         
    card_credit_account = fields.Many2one('account.account', string='Card Credit Account',
                                            domain="[('deprecated', '=', False), ('company_ids', 'in', company_id)]")



    def _get_journal_dashboard_data_batched(self):
        dashboard_data = super()._get_journal_dashboard_data_batched()
        self._fill_card_dashboard_data(dashboard_data)
        return dashboard_data
        # ~ self.env['account.move'].flush_model()
        # ~ self.env['account.move.line'].flush_model()
        # ~ self.env['account.payment'].flush_model()
        # ~ dashboard_data = {}  # container that will be filled by functions below
        # ~ for journal in self:
            # ~ dashboard_data[journal.id] = {
                # ~ 'currency_id': journal.currency_id.id or journal.company_id.sudo().currency_id.id,
                # ~ 'show_company': len(self.env.companies) > 1 or journal.company_id.id != self.env.company.id,
            # ~ }
        # ~ self._fill_bank_cash_dashboard_data(dashboard_data)
        # ~ self._fill_sale_purchase_dashboard_data(dashboard_data)
        # ~ self._fill_general_dashboard_data(dashboard_data)
        # ~ self._fill_onboarding_data(dashboard_data)
        # ~ return dashboard_data

    def _fill_card_dashboard_data(self, dashboard_data):
        """Populate all card journal's data dict with relevant information for the kanban card."""
        general_journals = self.filtered(lambda journal: journal.type == "card")
        if not general_journals:
            return
        to_check_vals = {
            journal.id: (amount_total_signed_sum, count)
            for journal, amount_total_signed_sum, count in self.env['account.move']._read_group(
                domain=[
                    *self.env['account.move']._check_company_domain(self.env.companies),
                    ('journal_id', 'in', general_journals.ids),
                    ('checked', '=', False),
                    ('state', '=', 'posted'),
                ],
                groupby=['journal_id'],
                aggregates=['amount_total_signed:sum', '__count'],
            )
        }
        for journal in general_journals:
            currency = journal.currency_id or self.env['res.currency'].browse(journal.company_id.sudo().currency_id.id)
            amount_total_signed_sum, count = to_check_vals.get(journal.id, (0, 0))
            drag_drop_settings = {
                'image': '/web/static/img/folder.svg',
                'text': _('Drop to create journal entries with attachments.'),
                'group': 'account.group_account_user',
            }

            dashboard_data[journal.id].update({
                'number_to_check': count,
                'to_check_balance': currency.format(amount_total_signed_sum),
                'drag_drop_settings': drag_drop_settings,
            })



    def open_action(self):
        _logger.warning("-------------------------------INSIDE OPEN ACTION ---------------------------------------")
        action = super().open_action()
        if self.type == "card":
            _logger.error("-------------------------------INSIDE CARD ---------------------------------------")
            ##Return an action that open account.card.statement which belong to this journal
            # _logger.error(str(self.open_action_with_context_mynt()))
            ctx = dict(self.env.context)
            action = {
                "type": "ir.actions.act_window",
                "name": "Card Statement",
                "res_model": "account.card.statement",
                "view_mode": "list,form",
                "domain": [("journal_id", "=", self.id)],
                "context": ctx,
            }
            return action
        return action



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
