# -*- coding: utf-8 -*-
"""Adopt the date range types from the retired bridge module.

Background
----------
``l10n_se_account_fiscal_year`` used to own all four ``date.range.type``
records (Fiscal Year, Quarter, Month, Week). It was created to resolve a
``UniqueViolation`` between ``account_fiscal_year_vrtl`` and
``l10n_se_date_ranges``, but it could not generate any ranges: its
``post_init_hook`` called ``generate_full_year()``, which only exists in
``l10n_se_date_ranges`` -- the module it replaced.

Ownership is now split by meaning:

    account_fiscal_year_vrtl   Fiscal Year, Month
    l10n_se_date_ranges        Quarter, Week

This migration re-points the ``ir.model.data`` rows for the two types this
module now owns. Moving the row (not the record) keeps ``res_id`` intact, so
every ``date.range.type_id`` keeps pointing at the same record.

Why a migration script and not pre_init_hook
--------------------------------------------
``pre_init_hook`` only runs when a module is *installed* (``state ==
'to install'``), never on upgrade -- see ``odoo/modules/loading.py``. An
upgraded database needs the adoption too, so it belongs here.

Order
-----
This runs before the module's data files are loaded, which is what makes it
work: the data file's ``<record>`` then *updates* the existing type instead
of trying to create a second one.
"""
import logging

_logger = logging.getLogger(__name__)

# Modules that owned these types before this one. Two cases exist in the
# fleet, and a database may be in either:
#
#   l10n_se_account_fiscal_year   the bridge module (2026-10-30 onwards)
#   l10n_se_date_ranges           before the bridge, up to 18.0.1.1.0
#
# A database that never upgraded past l10n_se_date_ranges 18.0.1.1.0 still has
# all four types under that module's xmlids. Adopting from only the bridge
# leaves those databases with adopted=0, and the data file then tries to
# create Fiscal Year and Month again -> UniqueViolation.
LEGACY_MODULES = (
    "l10n_se_account_fiscal_year",
    "l10n_se_date_ranges",
)
OWNED_XMLIDS = (
    "date_range_type_fiscalyear",
    "date_range_type_month",
)


def migrate(cr, version):
    if not version:
        # Fresh install: nothing to adopt, the data file creates the types.
        return

    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    Imd = env["ir.model.data"].sudo()

    adopted = 0
    for name in OWNED_XMLIDS:
        already = Imd.search([
            ("module", "=", "account_fiscal_year_vrtl"),
            ("name", "=", name),
            ("model", "=", "date.range.type"),
        ], limit=1)
        if already:
            continue

        for legacy_module in LEGACY_MODULES:
            legacy = Imd.search([
                ("module", "=", legacy_module),
                ("name", "=", name),
                ("model", "=", "date.range.type"),
            ], limit=1)
            if not legacy:
                continue
            legacy.write({"module": "account_fiscal_year_vrtl"})
            adopted += 1
            _logger.info(
                "Adopted date range type %s from %s (res_id %s).",
                name, legacy_module, legacy.res_id,
            )
            break

    _logger.info(
        "account_fiscal_year_vrtl 18.0.1.2.0: adopted %d date range type(s) "
        "from %s.", adopted, ", ".join(LEGACY_MODULES),
    )
