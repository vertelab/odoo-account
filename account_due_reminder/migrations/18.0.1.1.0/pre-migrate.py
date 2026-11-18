# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""Städa menyn som två filer deklarerade med samma xmlid.

Fram till 18.0.1.0.0 deklarerade `views/account_payment_plan_views.xml` och
`views/payment_reminder_line_views.xml` båda `id="account_payment_reminder_menu"`.
Den senare filen skrev över den förra, så bara en meny fanns i databasen.

Från 18.0.1.1.0 heter menyerna `menu_account_payment_plan` och
`menu_payment_reminder_line`. Det gamla xmlid:et blir en orphan: `ir.model.data`
pekar på en meny som ingen XML längre äger, och menyn blir kvar i menyträdet
utan att någon kan underhålla den.

Migreringen tar bort båda raderna — men bara om xmlid:et fortfarande pekar på
en meny vars action är en av de två kända. Ett återanvänt xmlid ska inte
raderas, och migreringen ska vara idempotent (den körs om vid varje
uppgradering som passerar versionen).
"""

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

LEGACY_XMLID = "account_due_reminder.account_payment_reminder_menu"
# De två actions som menyn kunde peka på, beroende på vilken fil som laddades sist.
KNOWN_ACTIONS = (
    "account_due_reminder.action_account_account_payment_plan",
    "account_due_reminder.action_account_payment_reminder_line",
)


def migrate(cr, version):
    """Ta bort den överskrivna menyn om den fortfarande finns."""
    if not version:
        # Nyinstallation: det gamla xmlid:et har aldrig funnits.
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    imd = env["ir.model.data"].search(
        [("module", "=", "account_due_reminder"),
         ("name", "=", "account_payment_reminder_menu"),
         ("model", "=", "ir.ui.menu")],
        limit=1,
    )
    if not imd:
        _logger.info("account_due_reminder: %s finns inte, inget att städa",
                     LEGACY_XMLID)
        return

    menu = env["ir.ui.menu"].browse(imd.res_id).exists()
    if not menu:
        # Xmlid utan meny — städa bara xmlid-raden.
        imd.unlink()
        _logger.info("account_due_reminder: tog bort xmlid %s (menyn saknades)",
                     LEGACY_XMLID)
        return

    action = menu.action
    action_xmlid = action.get_external_id().get(action.id) if action else None
    if action_xmlid not in KNOWN_ACTIONS:
        _logger.warning(
            "account_due_reminder: %s pekar på meny %s med action %s — "
            "känner inte igen den, lämnar menyn orörd",
            LEGACY_XMLID, menu.id, action_xmlid or (action and action.id),
        )
        return

    _logger.info(
        "account_due_reminder: tar bort överskriven meny %s (action %s)",
        menu.id, action_xmlid,
    )
    imd.unlink()
    menu.unlink()
