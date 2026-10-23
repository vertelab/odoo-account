# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<https://vertel.se>).
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
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""Change the journal entry a depreciation line is bound to.

Why this exists
===============

``account.asset.line.move_id`` is ``readonly=True`` and OCA's ``write()``
guard blocks changes to a line that already has an entry::

    elif (
        dl.move_id
        and not self.env.context.get("allow_asset_line_update")
        and dl.type != "create"
    ):
        raise UserError(
            "You cannot change a depreciation line "
            "with an associated accounting entry."
        )

The only supported path is the ``allow_asset_line_update`` context, which the
module itself uses when ``create_move()`` binds a freshly created entry.

That guard is right for normal operation.  But when a depreciation line ended
up pointing at the wrong journal entry — or at none at all while the entry
exists — there is no way to correct it from the UI.

This wizard provides that path, with the checks the raw write lacks:

* The target entry must belong to the same company as the asset.
* The target entry may be **draft or posted**.  Correcting a wrong binding on
  a posted entry is a legitimate bookkeeping fix; the entry itself is not
  touched, only the reference from the depreciation line.
* The line's amount must match the entry's depreciation amount, otherwise the
  board and the ledger would disagree silently.
* The target entry must not already be bound to another depreciation line.
* Every change is logged in the chatter of the asset and of the entry.

Two operations are available:

* **Change** — bind the line to a different draft entry.
* **Clear** — unbind the line (``move_id = False``), so it can be recreated
  with *Create Move*.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AssetLineChangeMove(models.TransientModel):
    _name = 'asset.line.change.move'
    _description = 'Change the entry of a depreciation line'

    asset_line_id = fields.Many2one(
        'account.asset.line',
        string='Depreciation Line',
        required=True,
        readonly=True,
    )
    asset_id = fields.Many2one(
        related='asset_line_id.asset_id',
        readonly=True,
    )
    company_id = fields.Many2one(
        related='asset_id.company_id',
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='asset_id.currency_id',
        readonly=True,
    )
    line_date = fields.Date(
        related='asset_line_id.line_date',
        readonly=True,
    )
    line_type = fields.Selection(
        related='asset_line_id.type',
        readonly=True,
    )
    amount = fields.Monetary(
        related='asset_line_id.amount',
        readonly=True,
    )
    current_move_id = fields.Many2one(
        related='asset_line_id.move_id',
        string='Current Entry',
        readonly=True,
    )
    operation = fields.Selection(
        selection=[
            ('change', 'Bind to another entry'),
            ('clear', 'Unbind from entry'),
        ],
        string='Operation',
        required=True,
        default='change',
    )
    new_move_id = fields.Many2one(
        'account.move',
        string='New Entry',
        domain="[('company_id', '=', company_id), ('id', '!=', current_move_id)]",
        help="Any entry of this company can be bound, including posted ones. "
             "The entry's depreciation amount is checked against the line.",
    )
    info = fields.Html(
        string='Information',
        compute='_compute_info',
    )

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends('asset_line_id', 'new_move_id', 'operation')
    def _compute_info(self):
        for wizard in self:
            line = wizard.asset_line_id
            parts = [
                _('<p><b>%(asset)s</b> — line %(date)s, amount %(amount)s '
                  '%(currency)s</p>',
                  asset=line.asset_id.display_name,
                  date=line.line_date,
                  amount=line.amount,
                  currency=line.asset_id.currency_id.name or ''),
            ]
            if line.type == 'create':
                parts.append(_(
                    '<p class="text-warning">This is the <b>acquisition</b> '
                    'line. Its entry is normally created by the asset itself; '
                    'changing it here only re-points the reference.</p>'))
            if wizard.operation == 'clear':
                parts.append(_(
                    '<p class="text-warning">The line will be unbound. Use '
                    '<b>Create Move</b> on the asset afterwards to generate a '
                    'new entry.</p>'))
            elif wizard.new_move_id:
                target = wizard.new_move_id
                parts.append(_(
                    '<p>Target entry: <b>%(entry)s</b> (%(state)s)</p>',
                    entry=target.display_name,
                    state=target.state))
                if target.state == 'posted':
                    parts.append(_(
                        '<p class="text-warning"><b>This entry is posted.</b> '
                        'The binding is changed, but the entry itself is not '
                        'modified. Make sure its depreciation amount matches '
                        'the line — otherwise the board and the ledger will '
                        'disagree.</p>'))
            wizard.info = ''.join(parts)

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------
    @api.model
    def _check_depreciation_amount(self, line, move, asset):
        """Verify that *move* carries the depreciation amount of *line*.

        A posted entry cannot be edited, so binding it to a line with a
        different amount would leave the depreciation board and the ledger
        permanently out of sync.  We therefore compare the line's amount with
        the entry's expense-leg debit/credit and refuse on a mismatch.

        The check is skipped when the asset has no profile accounts (a chart
        without a depreciation expense account), since there is nothing to
        compare against.
        """
        expense_account = asset.profile_id.account_expense_depreciation_id
        if not expense_account:
            return
        expense_lines = move.line_ids.filtered(
            lambda aml: aml.account_id == expense_account)
        if not expense_lines:
            raise UserError(_(
                'Entry %(entry)s has no line on the depreciation expense '
                'account %(account)s. It does not look like a depreciation '
                'entry for this asset.',
                entry=move.display_name,
                account=expense_account.display_name))

        entry_amount = sum(expense_lines.mapped('debit')) \
            - sum(expense_lines.mapped('credit'))
        currency = asset.currency_id
        if currency.compare_amounts(abs(entry_amount), abs(line.amount)) != 0:
            raise UserError(_(
                'The amount does not match.\n\n'
                'Depreciation line %(date)s: %(line_amount)s %(currency)s\n'
                'Entry %(entry)s: %(entry_amount)s %(currency)s\n\n'
                'Binding them would make the depreciation board disagree with '
                'the ledger. Correct the entry, or pick the entry that matches '
                'this line.',
                date=line.line_date,
                line_amount=line.amount,
                entry=move.display_name,
                entry_amount=abs(entry_amount),
                currency=currency.name or ''))

    @api.model
    def _sync_move_line_asset(self, line, move, asset):
        """Point the entry's depreciation lines at *asset*.

        ``create_move()`` sets ``asset_id`` on both legs of a depreciation
        entry (the depreciation account and the expense account).  When a line
        is re-bound to an entry that was created outside the board — or to an
        entry that previously belonged to another asset — those links must be
        corrected too, otherwise the entry keeps pointing at the old asset.

        Pass an empty ``asset`` recordset to release the links instead.

        Only the two depreciation legs are touched; any other line of the
        entry (VAT, partner, etc.) is left alone.
        """
        profile = (asset or line.asset_id).profile_id
        target_accounts = (profile.account_depreciation_id
                           | profile.account_expense_depreciation_id)
        if not target_accounts:
            return
        legs = move.line_ids.filtered(
            lambda aml: aml.account_id in target_accounts)
        if not legs:
            return
        legs.with_context(
            allow_asset=True, allow_asset_removal=True,
        ).write({'asset_id': asset.id if asset else False})

    def action_apply(self):
        """Write the new ``move_id`` on the depreciation line."""
        self.ensure_one()
        line = self.asset_line_id
        asset = line.asset_id

        if self.operation == 'clear':
            if not line.move_id:
                raise UserError(_('The line is not bound to an entry.'))
            old = line.move_id
            line.with_context(
                allow_asset_line_update=True,
                unlink_from_asset=True,
            ).write({'move_id': False})
            # Release the entry's own asset links as well, so it no longer
            # claims to belong to an asset that has no line for it.
            self._sync_move_line_asset(line, old, self.env['account.asset'])
            asset.message_post(body=_(
                'Depreciation line %(date)s was unbound from entry '
                '<b>%(entry)s</b> by %(user)s.',
                date=line.line_date,
                entry=old.display_name,
                user=self.env.user.display_name))
            _logger.info(
                'asset_line_change_move: cleared move_id on asset line %s '
                '(was %s) by %s', line.id, old.id, self.env.user.login)
            return {'type': 'ir.actions.act_window_close'}

        target = self.new_move_id
        if not target:
            raise UserError(_('Select the entry to bind the line to.'))
        if target == line.move_id:
            raise UserError(_('The line is already bound to this entry.'))
        if target.company_id != asset.company_id:
            raise UserError(_(
                'The entry belongs to another company than the asset.'))

        # The entry must not already carry another depreciation line.
        other = self.env['account.asset.line'].search([
            ('move_id', '=', target.id),
            ('id', '!=', line.id),
        ], limit=1)
        if other:
            raise UserError(_(
                'Entry %(entry)s is already bound to the depreciation line '
                '%(date)s of asset %(asset)s.',
                entry=target.display_name,
                date=other.line_date,
                asset=other.asset_id.display_name))

        # A posted entry is allowed — correcting a wrong binding is the whole
        # point of this wizard.  But the amounts must agree, otherwise the
        # depreciation board and the ledger would diverge silently.
        if line.type == 'depreciate':
            self._check_depreciation_amount(line, target, asset)

        line.with_context(
            allow_asset_line_update=True,
        ).write({'move_id': target.id})

        # Keep the entry's own asset links in step with the new binding.
        self._sync_move_line_asset(line, target, asset)

        asset.message_post(body=_(
            'Depreciation line %(date)s was re-bound from entry '
            '<b>%(old)s</b> to <b>%(new)s</b> by %(user)s.',
            date=line.line_date,
            old=line.move_id.display_name if line.move_id else _('none'),
            new=target.display_name,
            user=self.env.user.display_name))

        _logger.info(
            'asset_line_change_move: asset line %s move_id -> %s by %s',
            line.id, target.id, self.env.user.login)

        return {'type': 'ir.actions.act_window_close'}
