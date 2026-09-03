# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2026 Vertel AB (<https://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
##############################################################################

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Ensure account_move_line has deferred_id column if missing.

    The deferred_id field on account.move.line may not have been created
    as a database column during initial installation, for instance when
    migrating from an older module version or when the table already
    existed. This hook adds the column if missing to prevent schema errors.
    """
    cr = env.cr
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='account_move_line' AND column_name='deferred_id'"
    )
    if not cr.fetchone():
        cr.execute(
            "ALTER TABLE account_move_line "
            "ADD COLUMN deferred_id INT REFERENCES account_deferred(id)"
        )
        _logger.info("Added missing column account_move_line.deferred_id")
    _cleanup_legacy_rec_type_actions(env)


def _cleanup_legacy_rec_type_actions(env):
    """Heal stale actions/menus left by pre-2.1 module versions.

    Versions before 18.0.2.0.0 stored periodiseringar on ``account.asset``
    with a ``rec_type`` discriminator and created actions carrying
    ``rec_type`` domains. After the 2.1 rewrite the field only exists on
    ``account.deferred`` / ``account.deferred.profile``, so the leftover
    actions crash with "Invalid field account.asset.rec_type".

    This cleanup is idempotent: it runs on fresh installs (post_init_hook)
    and on upgrades through the migration post-migrate (18.0.2.2.0), and is
    a no-op on clean databases:
    * OCA asset actions are reset to an empty domain when ``rec_type`` is
      missing from their target model, so the Assets menus open again.
    * Orphaned legacy deferred actions/menus are deactivated.
    """
    # 1) Reset OCA asset actions whose domain references the dropped field.
    for xmlid in (
        "account_asset_management.account_asset_action",
        "account_asset_management.account_asset_profile_action",
    ):
        action = env.ref(xmlid, raise_if_not_found=False)
        if not action:
            continue
        # Check the live model (authoritative) instead of ir_model_fields:
        # during post-migration the stale ir_model_fields row for a removed
        # field may still exist (it is cleaned later in registry setup), which
        # would make the old guard skip the reset while the domain is already
        # invalid -> "Invalid field account.asset.rec_type" crash.
        if "rec_type" in env[action.res_model]._fields:
            # rec_type still exists on the model - the domain is valid.
            continue
        if action.domain and "rec_type" in action.domain:
            action.domain = "[]"
            _logger.info("Reset rec_type domain on %s", xmlid)

    # 2) Neutralize orphaned legacy deferred actions/menus.
    #
    # Type-aware: in Odoo 18 ``ir.actions.act_window`` has NO ``active``
    # field (base ir.actions.actions only exposes name/type/xml_id/path/
    # help/binding_*), so ``record.active`` on a leftover action raises
    # AttributeError and kills the whole upgrade. Menus (ir.ui.menu) keep
    # their ``active`` flag.
    #
    # The legacy menus still Reference their actions, so the actions are
    # NOT unlinked (would leave dangling References); instead their domain
    # is cleared so they no longer crash with "Invalid field
    # account.asset.rec_type", and the menus are soft-deactivated.
    _LEGACY_ACTION_IDS = (
        "account_deferred_expense_action",
        "account_deferred_income_action",
    )
    _LEGACY_MENU_IDS = (
        "account_deferred_expense_action_menu",
        "account_deferred_income_action_menu",
        "account_deferred_expense_profile_menu",
        "account_deferred_income_profile_menu",
    )
    for xmlid in _LEGACY_ACTION_IDS:
        action = env.ref(
            "account_deferred_revenue_expenses.%s" % xmlid,
            raise_if_not_found=False,
        )
        if not action:
            continue
        if "domain" in action._fields and action.domain:
            action.domain = "[]"
            _logger.info("Reset domain on legacy deferred action %s", xmlid)
    for xmlid in _LEGACY_MENU_IDS:
        record = env.ref(
            "account_deferred_revenue_expenses.%s" % xmlid,
            raise_if_not_found=False,
        )
        if record and hasattr(record, "active") and record.active:
            record.active = False
            _logger.info("Deactivated legacy deferred menu %s", xmlid)
