# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel Sverige AB (<https://vertel.se>).
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
"""Rename core's accounting root menu in place.

Why a hook and not a data file
==============================

``account.menu_finance`` is a translated ``char`` field stored as jsonb. A
``<record>`` in a data file does win over core's declaration on install, but
core's own data files are re-loaded on every ``account`` upgrade and then win
again -- the last writer takes the jsonb value. Measured on a test database:
a rename to "Accounting" reverted to "Invoicing" after ``checkmodule -m
account``.

Hooks run after every module's data files and translations have loaded, so
writing there makes this module the last writer. ``post_migrate_hook`` is
needed as well as ``post_init_hook``: an ``account`` upgrade does not
re-initialise this module, but it does re-run its data files.

Why rename instead of a second root
===================================

The previous implementation created a second root menu (``menu_accounting``)
and reparented core's children onto it from a hardcoded list. Any module that
declared a menu under ``account.menu_finance`` and was not in that list became
invisible -- ``account_dynamic_reports`` did exactly that. Renaming the core
root keeps every child, present and future, without a list to maintain.
"""

import logging

_logger = logging.getLogger(__name__)

ACCOUNTING_ROOT = 'account.menu_finance'
LEGACY_ROOT = 'account_accountant_ce.menu_accounting'

# Per-language labels for the accounting root. English stays "Accounting" (the
# Enterprise name this module exists to reproduce); Swedish reads "Bokföring",
# which is what a Swedish user expects and what Vertel's own terminology uses.
# Any language not listed falls back to the English label.
ROOT_NAME = {
    'en_US': 'Accounting',
    'en_GB': 'Accounting',
    'sv_SE': 'Bokföring',
}
ROOT_NAME_DEFAULT = 'Accounting'


def _apply_accounting_root(env):
    """Rename core's accounting root and hide it from the app switcher.

    Idempotent: writing the same values again is a no-op.
    """
    menu = env.ref(ACCOUNTING_ROOT, raise_if_not_found=False)
    if not menu:
        _logger.warning(
            "account_accountant_ce: %s not found, nothing to rename",
            ACCOUNTING_ROOT,
        )
        return

    # `name` is a translated char stored as jsonb, and write() only touches the
    # language in the current context. Writing once would set the active
    # language and leave every other one on core's value -- a Swedish user
    # would still read "Fakturering". So write once per active language, each
    # with its own label.
    langs = env['res.lang'].search([('active', '=', True)]).mapped('code')
    for lang in langs:
        label = ROOT_NAME.get(lang, ROOT_NAME_DEFAULT)
        menu.with_context(lang=lang).write({'name': label})

    # Core also carries an en_US value. It is inactive in most of our
    # databases (en_GB is the English one), but the key is still present and a
    # user with an inactive language would read core's "Invoicing" if the
    # language were activated later. Write it explicitly so the record has no
    # stale language left. Judging by the write above, Odoo does not keep a
    # separate jsonb key for an inactive language, so this only fills an
    # existing key -- it does not invent one.
    if 'en_US' not in langs:
        menu.with_context(lang='en_US').write({'name': ROOT_NAME['en_US']})

    # The icon is what puts a root menu in the app switcher. Core keeps its own
    # icon; we clear it so the app reads as "Accounting" via the category
    # rename in security/account_accountant_security.xml rather than as a
    # separate app tile.
    menu.write({'web_icon': False})
    _logger.info(
        "account_accountant_ce: %s renamed per language: %s",
        ACCOUNTING_ROOT,
        ", ".join("%s=%s" % (l, ROOT_NAME.get(l, ROOT_NAME_DEFAULT)) for l in langs),
    )


def _migrate_legacy_root(env):
    """Move children of the retired second root back onto core's root.

    Earlier versions of this module created ``menu_accounting`` and moved
    core's children onto it. Those databases still have the children there.
    Without this, the children would stay parented to a menu this module no
    longer declares, and the accounting app would render empty.
    """
    legacy = env.ref(LEGACY_ROOT, raise_if_not_found=False)
    if not legacy:
        return

    target = env.ref(ACCOUNTING_ROOT, raise_if_not_found=False)
    if not target:
        _logger.warning(
            "account_accountant_ce: legacy root %s found but %s is missing; "
            "leaving the legacy root in place",
            LEGACY_ROOT, ACCOUNTING_ROOT,
        )
        return

    children = legacy.child_id
    if children:
        _logger.info(
            "account_accountant_ce: moving %d menu(s) from %s back to %s",
            len(children), LEGACY_ROOT, ACCOUNTING_ROOT,
        )
        children.write({'parent_id': target.id})

    # Only unlink once it is empty; an unexpected child would otherwise be
    # orphaned.
    if not legacy.child_id:
        _logger.info(
            "account_accountant_ce: removing the retired root %s", LEGACY_ROOT
        )
        legacy.unlink()


def post_init_hook(env):
    _migrate_legacy_root(env)
    _apply_accounting_root(env)


def post_migrate_hook(env, version):
    _migrate_legacy_root(env)
    _apply_accounting_root(env)
