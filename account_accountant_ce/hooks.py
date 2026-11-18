# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""Upptäck menyer som ligger kvar under den dolda core-roten.

`data/account_accountant_data.xml` döljer `account.menu_finance` genom att
tömma dess `web_icon` och hänger om en fast lista av menyer till
`menu_accounting`. En meny som en annan modul hänger direkt under
`account.menu_finance` blir därför osynlig — den skapas, men renderas aldrig.

Listan i XML-filen kan inte bli komplett: den kan bara nämna moduler som
redan finns. Den här kontrollen larmar i stället för att tiga.

Varför en varning och inte ett fel: en meny under den dolda roten är ett
placeringsfel, inte ett installationsfel. Att krascha installationen skulle
göra en tredjepartsmodul oinstallerbar.

Begränsning: hooken körs vid installation/uppgradering av den här modulen.
Installerar man en annan modul senare kan den fortfarande hamna fel utan
larm — kör `check_hidden_root_menus` manuellt (eller läs menyträdet) efter
sådana installationer.
"""

import logging

import odoo
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# Menyerna som medvetet hänger under account.menu_finance och hängs om av
# data/account_accountant_data.xml. Allt annat där är en felplacering.
REPARENTED = [
    "account.menu_board_journal_1",
    "account.menu_finance_receivables",
    "account.menu_finance_payables",
    "account.menu_finance_entries",
    "account.menu_finance_reports",
    "account.menu_finance_configuration",
    "account_asset_management.menu_finance_assets",
]


def check_hidden_root_menus(env):
    """Logga en varning per meny som ligger kvar under den dolda roten."""
    root = env.ref("account.menu_finance", raise_if_not_found=False)
    if not root:
        return []

    allowed_ids = set()
    for xmlid in REPARENTED:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu:
            allowed_ids.add(menu.id)

    # Rå SQL, inte ORM: post_load körs innan registret är fyllt, så
    # env["ir.ui.menu"].search() returnerar tomt här.
    cr = env.cr
    query = "SELECT id FROM ir_ui_menu WHERE parent_id = %s"
    params = [root.id]
    if allowed_ids:
        query += " AND id NOT IN %s"
        params.append(tuple(allowed_ids))
    cr.execute(query, params)
    stray_ids = [row[0] for row in cr.fetchall()]
    if not stray_ids:
        return []

    # Rå SQL även för xmlid och namn. `menu.get_external_id()` går via
    # ir.model.data.model, och det fältet är inte registrerat ännu när
    # post_load körs:
    #   ValueError: Invalid field ir.model.data.model in leaf
    # Följden var att hela kontrollen kastade och fångades av
    # `except Exception` i post_load_hook — varningen uteblev alltså helt,
    # vilket är värre än att inte ha någon kontroll.
    cr.execute(
        "SELECT res_id, module, name FROM ir_model_data "
        "WHERE model = %s AND res_id IN %s",
        ("ir.ui.menu", tuple(stray_ids)),
    )
    xmlids = {row[0]: "%s.%s" % (row[1], row[2]) for row in cr.fetchall()}

    # Menynamnet är jsonb i Odoo 18 — läs det som text, inte via ORM.
    cr.execute(
        "SELECT id, name->>'en_US' FROM ir_ui_menu WHERE id IN %s",
        (tuple(stray_ids),),
    )
    names = dict(cr.fetchall())

    for menu_id in stray_ids:
        _logger.warning(
            "account_accountant_ce: menu %s ('%s') hangs under the hidden "
            "account.menu_finance and will not be visible. Parent it under "
            "account.menu_finance_reports (reports) or "
            "account.menu_finance_receivables (customer follow-up) instead.",
            xmlids.get(menu_id) or "ir.ui.menu,%s" % menu_id,
            names.get(menu_id),
        )
    return stray_ids


def post_load_hook():
    """Kör kontrollen efter att modulens data laddats.

    `post_init_hook` körs bara vid nyinstallation, inte vid uppgradering —
    och felet (en meny under den dolda roten) uppstår lika ofta när en annan
    modul installeras efteråt. `post_load_hook` körs vid varje registry-load
    med den här modulen installerad, alltså även efter att en annan modul
    lagt till en meny.
    """
    db_name = odoo.tools.config["db_name"]
    if not db_name:
        # Ingen databas vald (t.ex. `odoo --version`) — inget att kontrollera.
        return
    cr = odoo.sql_db.db_connect(db_name).cursor()
    try:
        check_hidden_root_menus(api.Environment(cr, SUPERUSER_ID, {}))
    except Exception:  # pragma: no cover - får aldrig stoppa en registry-load
        _logger.exception("account_accountant_ce: kunde inte kontrollera menyträdet")
    finally:
        cr.close()


def post_init_hook(env_or_cr, registry=None):
    """Kör kontrollen efter installation/uppgradering."""
    if registry is not None:
        # Odoo 17-serie signatur (cr, registry) — behåll för bakåtkompatibilitet.
        env = api.Environment(env_or_cr, SUPERUSER_ID, {})
    else:
        env = env_or_cr
    check_hidden_root_menus(env)
