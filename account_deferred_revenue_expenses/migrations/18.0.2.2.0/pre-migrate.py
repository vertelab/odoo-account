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

"""Pre-migration: stage legacy deferred records stored on account.asset.

Versions before 18.0.2.0.0 stored periodiseringar (deferred expenses /
income) on ``account.asset`` / ``account.asset.profile`` using a
``rec_type`` discriminator field. The 2.1 rewrite moved them to the
dedicated ``account.deferred`` models and removed the ``rec_type`` fields.

During a module upgrade the ``account.asset.rec_type`` column is dropped
mid-update, so this pre-migration copies the legacy deferred rows into
staging tables while the column still exists. The post-migration script
converts the staged rows into ``account.deferred`` records once the new
tables exist.
"""

import logging

_logger = logging.getLogger(__name__)

LEGACY_REC_TYPES = ("deferred_expense", "deferred_income")


def migrate(cr, version):
    """Stage legacy deferred records before account.asset.rec_type is dropped."""
    # Idempotency: only run while the legacy column still exists. On
    # already-upgraded databases the column is gone and there is nothing
    # to stage.
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='account_asset' AND column_name='rec_type'"
    )
    if not cr.fetchone():
        _logger.info(
            "account.asset.rec_type column not found - skipping legacy deferred "
            "pre-migration"
        )
        return

    # Re-run safety: a previous failed upgrade may already have created the
    # staging tables. Leave them in place for the post-migration to consume.
    cr.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name='account_deferred_legacy_migration_asset'"
    )
    if cr.fetchone():
        _logger.info(
            "Staging table account_deferred_legacy_migration_asset already "
            "exists - skipping staging"
        )
        return

    cr.execute(
        """
        CREATE TABLE account_deferred_legacy_migration_profile AS
        SELECT *
        FROM account_asset_profile
        WHERE rec_type IN %s
        """,
        (LEGACY_REC_TYPES,),
    )
    cr.execute(
        """
        CREATE TABLE account_deferred_legacy_migration_asset AS
        SELECT *
        FROM account_asset
        WHERE rec_type IN %s
        """,
        (LEGACY_REC_TYPES,),
    )
    cr.execute(
        """
        CREATE TABLE account_deferred_legacy_migration_line AS
        SELECT l.*
        FROM account_asset_line l
        JOIN account_deferred_legacy_migration_asset a ON a.id = l.asset_id
        """
    )

    cr.execute("SELECT count(*) FROM account_deferred_legacy_migration_profile")
    n_profiles = cr.fetchone()[0]
    cr.execute("SELECT count(*) FROM account_deferred_legacy_migration_asset")
    n_assets = cr.fetchone()[0]
    cr.execute("SELECT count(*) FROM account_deferred_legacy_migration_line")
    n_lines = cr.fetchone()[0]
    _logger.info(
        "Staged %s legacy deferred profiles, %s assets and %s lines for migration",
        n_profiles,
        n_assets,
        n_lines,
    )
