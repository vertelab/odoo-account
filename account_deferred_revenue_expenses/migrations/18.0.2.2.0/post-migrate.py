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

"""Post-migration: convert staged legacy deferred data into account.deferred.

Reads the staging tables created by pre-migrate (legacy ``account.asset``
rows with ``rec_type='deferred_expense'`` / ``'deferred_income'`` and their
profiles/lines) and creates ``account.deferred`` /
``account.deferred.profile`` / ``account.deferred.line`` records. Real
assets (``rec_type='asset'``) are never touched.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

_STATE_MAP = {
    "draft": "draft",
    "open": "open",
    "close": "close",
    "removed": "close",
}


def migrate(cr, version):
    """Convert staged legacy deferred data into the new models."""
    cr.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name='account_deferred_legacy_migration_asset'"
    )
    if cr.fetchone():
        env = api.Environment(cr, SUPERUSER_ID, {})
        profile_map = _migrate_profiles(cr, env)
        asset_map = _migrate_assets(cr, env, profile_map)
        _migrate_lines(cr, env, asset_map)

        cr.execute("DROP TABLE IF EXISTS account_deferred_legacy_migration_profile")
        cr.execute("DROP TABLE IF EXISTS account_deferred_legacy_migration_asset")
        cr.execute("DROP TABLE IF EXISTS account_deferred_legacy_migration_line")
        _logger.info(
            "Legacy deferred migration complete: %s profiles, %s deferred entries",
            len(profile_map),
            len(asset_map),
        )
    else:
        _logger.info("No staged legacy deferred data - skipping post-migration")

    # Stale action/menu cleanup must run on every upgrade, not only on
    # install. post_init_hook only runs on new installs, so it is also
    # executed here (idempotent, a no-op on clean databases).
    from odoo.addons.account_deferred_revenue_expenses.hooks import (
        _cleanup_legacy_rec_type_actions,
    )

    env = api.Environment(cr, SUPERUSER_ID, {})
    _cleanup_legacy_rec_type_actions(env)


def _migrate_profiles(cr, env):
    """Convert legacy account.asset.profile rows into account.deferred.profile.

    Account mapping (confirmed against production data):
      account.asset.profile.account_depreciation_id
          -> account.deferred.profile.account_depreciation_id
      account.asset.profile.account_expense_depreciation_id
          -> account.deferred.profile.account_expense_id
    """
    cr.execute(
        """
        SELECT id, name, active, company_id, rec_type,
               account_depreciation_id, account_expense_depreciation_id,
               journal_id, method_number, method_period, note
        FROM account_deferred_legacy_migration_profile
        """
    )
    profile_model = env["account.deferred.profile"]
    profile_map = {}
    for row in cr.fetchall():
        (pid, name, active, company_id, rec_type, acc_dep, acc_exp, journal_id,
         method_number, method_period, note) = row
        profile = profile_model.create({
            "name": name,
            "active": bool(active) if active is not None else True,
            "company_id": company_id,
            "rec_type": rec_type,
            "account_depreciation_id": acc_dep,
            "account_expense_id": acc_exp,
            "journal_id": journal_id,
            "method_number": method_number or 12,
            "method_period": method_period or "month",
            "note": note,
        })
        profile_map[pid] = profile.id
    return profile_map


def _migrate_assets(cr, env, profile_map):
    """Convert legacy account.asset deferred rows into account.deferred."""
    cr.execute(
        """
        SELECT id, name, code, profile_id, rec_type, partner_id, company_id,
               COALESCE(depreciation_base, purchase_value) AS amount_total,
               date_start, method_period, method_number, state
        FROM account_deferred_legacy_migration_asset
        """
    )
    deferred_model = env["account.deferred"]
    profile_model = env["account.deferred.profile"]
    asset_map = {}
    for row in cr.fetchall():
        (aid, name, code, profile_id, rec_type, partner_id, company_id,
         amount_total, date_start, method_period, method_number, state) = row
        new_profile_id = profile_map.get(profile_id)
        if not new_profile_id:
            _logger.warning(
                "Skipping legacy deferred entry %s (%s): no converted profile "
                "for account.asset.profile %s",
                aid,
                name,
                profile_id,
            )
            continue
        profile = profile_model.browse(new_profile_id)
        deferred = deferred_model.create({
            "name": name,
            "code": code,
            "profile_id": new_profile_id,
            "rec_type": rec_type,
            "partner_id": partner_id,
            "company_id": company_id,
            "account_depreciation_id": profile.account_depreciation_id.id,
            "account_expense_id": profile.account_expense_id.id,
            "journal_id": profile.journal_id.id,
            "amount_total": amount_total,
            "date_start": date_start,
            "method_period": method_period or "month",
            "method_number": method_number or 12,
            "state": _STATE_MAP.get(state, "draft"),
        })
        asset_map[aid] = deferred.id
    return asset_map


def _migrate_lines(cr, env, asset_map):
    """Convert legacy account.asset.line stubs into account.deferred.line."""
    if not asset_map:
        return
    cr.execute(
        """
        SELECT id, asset_id, name, line_date, amount, move_id
        FROM account_deferred_legacy_migration_line
        ORDER BY asset_id, type, line_date
        """
    )
    line_model = env["account.deferred.line"]
    counter = {}
    created = 0
    for row in cr.fetchall():
        (_lid, asset_id, name, line_date, amount, move_id) = row
        deferred_id = asset_map.get(asset_id)
        if not deferred_id:
            continue
        counter[deferred_id] = counter.get(deferred_id, 0) + 1
        line_model.create({
            "deferred_id": deferred_id,
            "name": name,
            "sequence": counter[deferred_id] * 10,
            "date": line_date,
            "amount": amount,
            "posted": bool(move_id),
            "move_id": move_id,
        })
        created += 1
    _logger.info("Migrated %s legacy deferred lines", created)
