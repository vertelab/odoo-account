# Copyright 2026 Vertel AB (<https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

"""Upgrade to 18.0.2.4.0.

The A/B booking-model semantics were clarified and re-labelled:
   old A_explicit_prepaid  -> A_visma_cost_entry   (Visma-style: bill on cost account,
                                                    module parks net cost on interim at post)
   old B_auto_defer        -> B_fortnox_interim_entry (Fortnox-style: bill coded directly
                                                    on the interim account; no rebook)

Databases that already ran 18.0.2.2.0/18.0.2.3.0 may hold the OLD enum string values in
res_company.deferred_booking_method. Rewrite them. Companies that never set one get the
new default (B_fortnox_interim_entry). Safe to re-run (guarded).
"""

import logging

_logger = logging.getLogger(__name__)

_DEFAULT = 'B_fortnox_interim_entry'
_VALUE_MAP = {
    'A_explicit_prepaid': 'A_visma_cost_entry',
    'B_auto_defer': 'B_fortnox_interim_entry',
}


def migrate(cr, version):
    # 1) Ensure column exists (ORM normally creates it from the field definition).
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='res_company' AND column_name='deferred_booking_method'"
    )
    if not cr.fetchone():
        cr.execute(
            "ALTER TABLE res_company ADD COLUMN deferred_booking_method VARCHAR");
        cr.execute(
            "UPDATE res_company SET deferred_booking_method = %s", (_DEFAULT,))
        _logger.info("Added res_company.deferred_booking_method default %s", _DEFAULT)

    # 2) Rewrite legacy enum strings.
    for old, new in _VALUE_MAP.items():
        cr.execute(
            "UPDATE res_company SET deferred_booking_method = %s "
            "WHERE deferred_booking_method = %s",
            (new, old))
        if cr.rowcount:
            _logger.info(
                "Rewrote %s res_company row(s): %s -> %s", cr.rowcount, old, new)

    # 3) Backfill companies still NULL/empty with the default.
    cr.execute(
        "UPDATE res_company SET deferred_booking_method = %s "
        "WHERE deferred_booking_method IS NULL OR deferred_booking_method = ''",
        (_DEFAULT,))
