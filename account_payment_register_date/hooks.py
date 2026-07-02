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

from odoo import fields, models

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Ensure account_move_line has deferred_id column if missing.

    The account_deferred_revenue_expenses module adds a deferred_id
    field to account.move.line, but the database column may not have
    been created during initial installation. This hook adds it if
    missing to prevent schema errors in the payment register wizard.
    """
    if env['ir.module.module'].search_count([
        ('name', '=', 'account_deferred_revenue_expenses'),
        ('state', '=', 'installed'),
    ]):
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
