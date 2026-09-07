# Copyright 2026 Vertel AB (<https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

"""Upgrade to 18.0.2.3.0.

* Ensures ``res_company.deferred_booking_method`` exists (the ORM normally
  creates it from the field definition; this is a defensive no-op guard).
* Drops the no-longer-used ``account_deferred_profile.use_line_account``
  column (the field was removed; Odoo does not auto-drop columns, so we do it
  here).

Everything is guarded via ``information_schema`` so re-running is safe, and on
databases that were already migrated by other means (fresh createdb / forced
update where the column is absent) each step is a no-op.
"""

import logging

_logger = logging.getLogger(__name__)

_DEFAULT_BOOKING_METHOD = 'B_auto_defer'


def migrate(cr, version):
    # 1) Ensure the company booking-method column exists with default B.
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='res_company' AND column_name='deferred_booking_method'"
    )
    if not cr.fetchone():
        cr.execute(
            "ALTER TABLE res_company "
            "ADD COLUMN deferred_booking_method VARCHAR "
            "DEFAULT %s",
            (_DEFAULT_BOOKING_METHOD,),
        )
        cr.execute("UPDATE res_company SET deferred_booking_method = %s", (
            _DEFAULT_BOOKING_METHOD,))
        _logger.info(
            "Added res_company.deferred_booking_method with default %s",
            _DEFAULT_BOOKING_METHOD,
        )
    else:
        _logger.info("res_company.deferred_booking_method already exists")

    # 2) Drop the removed per-profile use_line_account column if present.
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='account_deferred_profile' AND column_name='use_line_account'"
    )
    if cr.fetchone():
        cr.execute(
            "ALTER TABLE account_deferred_profile DROP COLUMN use_line_account"
        )
        _logger.info("Dropped account_deferred_profile.use_line_account")
    else:
        _logger.info(
            "account_deferred_profile.use_line_account already absent - skipping"
        )
