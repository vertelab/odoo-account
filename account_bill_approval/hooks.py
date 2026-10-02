# Copyright 2026 Vertel AB
# SPDX-License-Identifier: AGPL-3
"""Install-time guards for the vendor bill approval module.

``bill.approval.user.line`` is declared with ``_name`` both here and in the
legacy Linserv module ``purchase_vendor_bill_approval``.  Odoo keeps exactly
one registry class per model name: the module loaded *last* wins and the other
class is dropped entirely (see ``BaseModel._build_model`` — a class that sets
``_name`` without listing it in ``_inherit`` replaces the existing class
instead of extending it).  Modules are loaded in name order, so
``purchase_vendor_bill_approval`` is loaded after ``account_bill_approval``
and its class replaces ours.

The result is silent and confusing: the database table and the views still
reference ``date_rejected``, ``company_id``, ``rejected_by_id``,
``reject_reason`` and ``ret_bill_approval_count``, but the running model does
not have them.  The web client then raises::

    "bill.approval.user.line"."date_rejected" field is undefined.

The two modules therefore must never be installed at the same time.  The
legacy module has to be uninstalled — that is what
``account_bill_approval_migration`` prepares (it hands the ``ir.model``
ownership over so the table survives).
"""

import logging

from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

LEGACY_MODULE = "purchase_vendor_bill_approval"
MIGRATION_MODULE = "account_bill_approval_migration"
MODEL_NAME = "bill.approval.user.line"


def _module_states(env, names):
    """Return ``{module_name: state}`` for the given module names."""
    records = env["ir.module.module"].sudo().search_read(
        [("name", "in", names)], ["name", "state"],
    )
    return {record["name"]: record["state"] for record in records}


def pre_init_hook(env):
    """Refuse to install next to the legacy module without the bridge.

    Installing this module while ``purchase_vendor_bill_approval`` is
    installed cripples the model (see the module docstring).  The supported
    way is to install ``account_bill_approval_migration`` in the same run and
    then uninstall the legacy module.

    ``pre_init_hook`` only runs on a fresh install, so an upgrade of an
    already broken database is not blocked here — ``post_init_hook`` logs a
    critical error for that case instead.
    """
    states = _module_states(env, [LEGACY_MODULE, MIGRATION_MODULE])
    legacy_state = states.get(LEGACY_MODULE, "uninstalled")
    if legacy_state not in ("installed", "to upgrade"):
        return

    migration_state = states.get(MIGRATION_MODULE, "uninstalled")
    if migration_state in ("installed", "to install", "to upgrade"):
        _logger.warning(
            "account_bill_approval: %s is still installed; the module "
            "ownership of %s is handled by %s. Uninstall %s afterwards.",
            LEGACY_MODULE, MODEL_NAME, MIGRATION_MODULE, LEGACY_MODULE,
        )
        return

    raise UserError(_(
        "The legacy module '%(legacy)s' is still installed and it declares "
        "the model '%(model)s' with the same technical name as this module.\n\n"
        "Odoo keeps only one model class per name — the module loaded last "
        "wins — so installing '%(new)s' next to it would silently drop the "
        "fields 'date_rejected', 'company_id', 'rejected_by_id' and "
        "'reject_reason' from the running model while the database and the "
        "views still use them.\n\n"
        "Install '%(migration)s' together with this module and uninstall "
        "'%(legacy)s' afterwards (see its README for the exact order).",
        legacy=LEGACY_MODULE,
        model=MODEL_NAME,
        new="account_bill_approval",
        migration=MIGRATION_MODULE,
    ))


def post_init_hook(env):
    """Warn loudly when the broken combination is already in place.

    A database where this module was installed before the guard existed (or
    where the legacy module was installed afterwards) is left with a model
    that lacks the fields the views expect.  Nothing can repair that from
    here — the legacy module has to be uninstalled — but the log must say so
    instead of letting the user discover an Owl error in the browser.
    """
    states = _module_states(env, [LEGACY_MODULE])
    if states.get(LEGACY_MODULE) not in ("installed", "to upgrade"):
        return

    _logger.critical(
        "account_bill_approval: %s is installed alongside %s. Both declare "
        "the model %s with '_name', and %s is loaded last, so its class "
        "replaces the one from this module: 'date_rejected', 'company_id', "
        "'rejected_by_id', 'reject_reason' and 'ret_bill_approval_count' are "
        "missing from the running model while the views and the table still "
        "use them. Install %s and uninstall %s to repair.",
        LEGACY_MODULE, "account_bill_approval", MODEL_NAME, LEGACY_MODULE,
        MIGRATION_MODULE, LEGACY_MODULE,
    )
