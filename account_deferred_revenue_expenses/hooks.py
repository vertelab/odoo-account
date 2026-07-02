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
