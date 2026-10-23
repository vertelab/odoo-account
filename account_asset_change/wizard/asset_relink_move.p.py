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
"""Re-link the journal entry (``account.move``) to a different asset.

Why this exists
===============

OCA's ``account_asset_management`` blocks any write of ``asset_id`` on a move
line::

    FIELDS_AFFECTS_ASSET_MOVE_LINE = {
        "credit", "debit", "account_id", "journal_id", "date",
        "asset_profile_id", "asset_id",
    }
    ...
    if set(vals).intersection(FIELDS_AFFECTS_ASSET_MOVE_LINE) and not (
        self.env.context.get("allow_asset_removal")
        and list(vals.keys()) == ["asset_id"]
    ):
        raise UserError("You cannot change an accounting item linked to an
                         asset depreciation line.")

The link can therefore only be changed with ``allow_asset`` +
``allow_asset_removal`` in the context, and only when ``asset_id`` is the
single key written.

That guard is right for normal operation, but when the wrong invoice was
linked to an asset (a real bookkeeping error) there is no supported way to
fix it from the UI.

This wizard works from the **journal entry**, not from the asset:

* Open an invoice or misc entry, press **Re-link Asset** in the button box.
* The wizard lists every line of that entry that carries an asset link.
* For each line, pick the asset that should own it — or clear it.
* All lines are written in one go, with the context OCA requires, and every
  change is logged in the chatter of the entry and of both assets.

Safety rails the raw write lacks
--------------------------------
* Only **draft** entries can be re-linked.  A posted entry must be reversed
  first, otherwise the depreciation board would no longer match the ledger.
* Only lines belonging to the asset's **acquisition** entry may be moved.
  Depreciation entries follow the asset automatically.
* The target asset must belong to the same company.
* The line's account must match the target asset's asset account.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AssetRelinkMove(models.TransientModel):
    _name = 'asset.relink.move'
    _description = 'Re-link journal entry to another asset'

    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        required=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related='move_id.company_id',
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='move_id.currency_id',
        readonly=True,
    )
    line_ids = fields.One2many(
        'asset.relink.move.line',
        'wizard_id',
        string='Lines',
    )
    state = fields.Selection(
        related='move_id.state',
        readonly=True,
    )
    warning = fields.Html(
        string='Warning',
        compute='_compute_warning',
    )

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        """Pre-fill one row per asset-linked line of the entry.

        Only used when the wizard is opened through the form view.  The same
        population happens in :meth:`create` so the wizard also works when it
        is instantiated programmatically (tests, server actions).
        """
        defaults = super().default_get(fields_list)
        move_id = defaults.get('move_id') or self.env.context.get('default_move_id')
        if not move_id:
            return defaults
        defaults['line_ids'] = self._prepare_line_commands(move_id)
        return defaults

    @api.model
    def _prepare_line_commands(self, move_id):
        """Return one ``Command.create`` per asset-linked line of *move_id*."""
        move = self.env['account.move'].browse(move_id)
        return [
            fields.Command.create({
                'move_line_id': line.id,
                'current_asset_id': line.asset_id.id,
                'new_asset_id': line.asset_id.id,
            })
            for line in move.line_ids.filtered('asset_id')
        ]

    @api.model_create_multi
    def create(self, vals_list):
        """Populate the line rows when the wizard is created directly."""
        for vals in vals_list:
            if not vals.get('line_ids') and vals.get('move_id'):
                vals['line_ids'] = self._prepare_line_commands(vals['move_id'])
        return super().create(vals_list)

    @api.depends('move_id', 'line_ids')
    def _compute_warning(self):
        for wizard in self:
            parts = []
            if wizard.move_id.state != 'draft':
                parts.append(_(
                    '<p class="text-danger"><b>This entry is posted.</b> '
                    'Reverse it before re-linking — otherwise the '
                    'depreciation board no longer matches the ledger.</p>'))
            if not wizard.line_ids:
                parts.append(_(
                    '<p class="text-muted">This entry has no lines linked to '
                    'an asset.</p>'))
            else:
                parts.append(_(
                    '<p>Lines marked <b>acquisition</b> can be re-linked. '
                    'Depreciation lines follow their asset automatically and '
                    'are shown read-only.</p>'))
            wizard.warning = ''.join(parts)

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------
    def action_apply(self):
        """Write the new asset links."""
        self.ensure_one()
        move = self.move_id

        if move.state != 'draft':
            raise UserError(_(
                'The journal entry %(entry)s is posted. Reverse it before '
                're-linking it to another asset.',
                entry=move.name or move.display_name))

        changed = 0
        for row in self.line_ids:
            line = row.move_line_id
            if not line.exists():
                continue
            if line.move_id != move:
                raise UserError(_(
                    'Line %(line)s does not belong to entry %(entry)s.',
                    line=line.display_name, entry=move.display_name))
            if row.new_asset_id == row.current_asset_id:
                continue

            # Only the acquisition entry may be re-linked.
            if row.current_asset_id and not self._is_acquisition_line(
                    line, row.current_asset_id):
                raise UserError(_(
                    'Line "%(name)s" is part of a depreciation entry and '
                    'cannot be re-linked. Depreciation entries follow the '
                    'asset automatically.',
                    name=line.name or line.display_name))

            target = row.new_asset_id
            if target:
                if target.company_id != move.company_id:
                    raise UserError(_(
                        'You cannot link an entry to an asset in another '
                        'company.'))
                target_account = (target.account_asset_id
                                  or target.profile_id.account_asset_id)
                if target_account and line.account_id != target_account:
                    raise UserError(_(
                        'Line "%(name)s" is booked on %(line_account)s but '
                        'asset %(asset)s uses %(asset_account)s. Re-book the '
                        'line on the correct account first.',
                        name=line.name or line.display_name,
                        line_account=line.account_id.display_name,
                        asset=target.display_name,
                        asset_account=target_account.display_name))

            line.with_context(
                allow_asset=True, allow_asset_removal=True,
            ).write({'asset_id': target.id if target else False})
            changed += 1

            # Chatter on the entry and on both assets.
            entry_label = move.name or move.display_name
            if target:
                move.message_post(body=_(
                    'Line "%(name)s" was re-linked from asset '
                    '<b>%(old)s</b> to <b>%(new)s</b> by %(user)s.',
                    name=line.name or line.display_name,
                    old=row.current_asset_id.display_name or _('none'),
                    new=target.display_name,
                    user=self.env.user.display_name))
                target.message_post(body=_(
                    'Entry <b>%(entry)s</b> was linked to this asset by '
                    '%(user)s.',
                    entry=entry_label,
                    user=self.env.user.display_name))
                if row.current_asset_id:
                    row.current_asset_id.message_post(body=_(
                        'Entry <b>%(entry)s</b> was unlinked from this asset '
                        'by %(user)s.',
                        entry=entry_label,
                        user=self.env.user.display_name))
            else:
                move.message_post(body=_(
                    'Line "%(name)s" was detached from asset <b>%(old)s</b> '
                    'by %(user)s.',
                    name=line.name or line.display_name,
                    old=row.current_asset_id.display_name or _('none'),
                    user=self.env.user.display_name))
                if row.current_asset_id:
                    row.current_asset_id.message_post(body=_(
                        'Entry <b>%(entry)s</b> was unlinked from this asset '
                        'by %(user)s.',
                        entry=entry_label,
                        user=self.env.user.display_name))

            _logger.info(
                'asset_relink: move line %s re-linked %s -> %s (user %s)',
                line.id, row.current_asset_id.id or 0, target.id or 0,
                self.env.user.login)

        if not changed:
            raise UserError(_('Nothing to change — no line was modified.'))

        # Recompute the affected depreciation boards.
        assets = self.line_ids.mapped('current_asset_id') | self.line_ids.mapped(
            'new_asset_id')
        for asset in assets:
            try:
                asset.compute_depreciation_board()
            except Exception:  # noqa: BLE001 - never block the re-link
                _logger.warning(
                    'asset_relink: could not recompute board for asset %s',
                    asset.id, exc_info=True)

        return {'type': 'ir.actions.act_window_close'}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _is_acquisition_line(self, line, asset):
        """Return True when *line* belongs to *asset*'s acquisition entry.

        OCA sets ``asset_id`` on **every** line of a depreciation entry, so
        ``line.asset_id == asset`` is not enough to tell an acquisition entry
        from a depreciation entry.

        An acquisition entry is recognised by:

        1. its move being the one referenced by the asset's ``type='create'``
           board line, or
        2. the asset having no ``create`` line bound to a move yet (the board
           is only planned), in which case the line is accepted when it sits
           on the asset's own asset account.

        Depreciation and removal entries are rejected.
        """
        board = asset.depreciation_line_ids

        if board.filtered(
                lambda al: al.type in ('depreciate', 'remove')
                and al.move_id and al.move_id == line.move_id):
            return False

        if board.filtered(
                lambda al: al.type == 'create'
                and al.move_id and al.move_id == line.move_id):
            return True

        bound_create = board.filtered(
            lambda al: al.type == 'create' and al.move_id)
        if bound_create:
            return False

        asset_account = (asset.account_asset_id
                         or asset.profile_id.account_asset_id)
        return bool(asset_account) and line.account_id == asset_account


class AssetRelinkMoveLine(models.TransientModel):
    _name = 'asset.relink.move.line'
    _description = 'Re-link journal entry line'

    wizard_id = fields.Many2one(
        'asset.relink.move',
        required=True,
        ondelete='cascade',
    )
    move_line_id = fields.Many2one(
        'account.move.line',
        string='Journal Item',
        required=True,
        readonly=True,
    )
    name = fields.Char(
        related='move_line_id.name',
        string='Label',
        readonly=True,
    )
    account_id = fields.Many2one(
        related='move_line_id.account_id',
        string='Account',
        readonly=True,
    )
    debit = fields.Monetary(
        related='move_line_id.debit',
        readonly=True,
    )
    credit = fields.Monetary(
        related='move_line_id.credit',
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='wizard_id.currency_id',
        readonly=True,
    )
    current_asset_id = fields.Many2one(
        'account.asset',
        string='Current Asset',
        readonly=True,
    )
    new_asset_id = fields.Many2one(
        'account.asset',
        string='New Asset',
        domain="[('company_id', '=', parent.company_id)]",
        help="Leave empty to detach the line from its asset.",
    )
