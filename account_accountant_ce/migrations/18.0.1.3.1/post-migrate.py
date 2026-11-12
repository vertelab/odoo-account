# -*- coding: utf-8 -*-
"""Re-apply the accounting root rename after an upgrade.

`post_init_hook` only runs on a fresh install -- Odoo 18 has no
`post_migrate_hook`, and an upgrade calls neither. A migration script is the
only place that runs on every upgrade.

It is needed because core's data files are re-loaded on every `account`
upgrade and win the jsonb write: measured on a test database, the name went
back to "Invoicing" after `checkmodule -m account`. This module's own data
files load after core's, but they are only re-loaded when *this* module is
upgraded -- not when `account` is. So the name survives an `account` upgrade
only if something re-applies it afterwards, which is what this does on the
next upgrade of this module.
"""

import logging

_logger = logging.getLogger(__name__)

ACCOUNTING_ROOT = 'account.menu_finance'
LEGACY_ROOT = 'account_accountant_ce.menu_accounting'

ROOT_NAME = {
    'en_US': 'Accounting',
    'en_GB': 'Accounting',
    'sv_SE': 'Bokföring',
}
ROOT_NAME_DEFAULT = 'Accounting'


def _apply_accounting_root(env):
    menu = env.ref(ACCOUNTING_ROOT, raise_if_not_found=False)
    if not menu:
        _logger.warning(
            "account_accountant_ce: %s not found, nothing to rename",
            ACCOUNTING_ROOT)
        return

    langs = env['res.lang'].search([('active', '=', True)]).mapped('code')
    for lang in langs:
        label = ROOT_NAME.get(lang, ROOT_NAME_DEFAULT)
        menu.with_context(lang=lang).write({'name': label})

    if 'en_US' not in langs:
        menu.with_context(lang='en_US').write({'name': ROOT_NAME['en_US']})

    menu.write({'web_icon': False})
    _logger.info(
        "account_accountant_ce: renamed %s per language: %s",
        ACCOUNTING_ROOT,
        ', '.join('%s=%s' % (l, ROOT_NAME.get(l, ROOT_NAME_DEFAULT))
                  for l in langs))


def _migrate_legacy_root(env):
    legacy = env.ref(LEGACY_ROOT, raise_if_not_found=False)
    if not legacy:
        return
    target = env.ref(ACCOUNTING_ROOT, raise_if_not_found=False)
    if not target:
        _logger.warning(
            "account_accountant_ce: %s missing, cannot migrate %s",
            ACCOUNTING_ROOT, LEGACY_ROOT)
        return
    children = legacy.child_id
    if children:
        children.write({'parent_id': target.id})
    if not legacy.child_id:
        legacy.unlink()


def migrate(cr, version):
    if not version:
        return
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    _migrate_legacy_root(env)
    _apply_accounting_root(env)
