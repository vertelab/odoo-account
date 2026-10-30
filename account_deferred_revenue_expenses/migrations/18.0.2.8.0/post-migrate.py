# -*- coding: utf-8 -*-
"""T/11823 - backfill the deferred reference number from the origin invoice.

Before 18.0.2.8.0 ``code`` was only filled by the creation wizard, and only
with ``account.move.name`` at that moment - which is ``/`` while the invoice
is still a draft. Entries created from a draft invoice therefore ended up
with an empty or meaningless reference. This migration fills those rows from
the (now posted) invoice number.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    from odoo import SUPERUSER_ID, api

    from odoo.addons.account_deferred_revenue_expenses.hooks import (
        _backfill_deferred_code,
    )

    env = api.Environment(cr, SUPERUSER_ID, {})
    _backfill_deferred_code(env)
    _logger.info("T/11823: deferred reference numbers backfilled")
