# Copyright 2026 Vertel AB
# SPDX-License-Identifier: AGPL-3
"""One-shot migration from the legacy Linserv module.

The legacy module ``purchase_vendor_bill_approval`` owns
``ir.model`` / ``ir.model.fields`` / ``ir.model.access`` records for the
model ``bill.approval.user.line``. When it is uninstalled Odoo calls
``ir.model._drop_table()`` which runs ``DROP TABLE ... CASCADE`` — the
approval history would be lost even though the new module declares the
same model.

This hook therefore:

1. takes a safety copy of the table,
2. adds the new columns,
3. back-fills ``company_id`` from the related bill,
4. **transfers ownership** of the ``ir_model_data`` rows from the legacy
   module to ``account_bill_approval``, so that uninstalling the legacy
   module can no longer drop the table.

Step 4 is the critical one. Without it the data is gone.
"""

import logging

_logger = logging.getLogger(__name__)

LEGACY_MODULE = "purchase_vendor_bill_approval"
NEW_MODULE = "account_bill_approval"
TABLE = "bill_approval_user_line"
BACKUP_TABLE = "bill_approval_user_line_backup"

# ir_model_data rows that must follow the model to the new module.
# ``model`` is the ir.model_data.model column (the technical model name of
# the record being described), not the model that owns the table.
OWNERSHIP_ROWS = [
    ("ir.model", "model_bill_approval_user_line"),
    ("ir.model.fields", "field_bill_approval_user_line__%"),
    ("ir.model.fields.selection", "selection__bill_approval_user_line__%"),
    ("ir.model.access", "access_bill_approval_user_line_%"),
]


def post_init_hook(env):
    """Run the migration. Safe to re-run (idempotent)."""
    cr = env.cr

    if not _table_exists(cr, TABLE):
        _logger.info(
            "account_bill_approval_migration: table %s does not exist, "
            "nothing to migrate.", TABLE,
        )
        return

    _logger.info("account_bill_approval_migration: starting migration")

    _backup_table(cr)
    _add_columns(cr)
    _backfill_company(cr)
    _transfer_ownership(cr)

    cr.commit()
    _logger.info("account_bill_approval_migration: migration complete")


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _table_exists(cr, table):
    cr.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = %s
    """, (table,))
    return bool(cr.fetchone())


def _column_exists(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


def _backup_table(cr):
    """Create a safety copy — never overwrite an existing backup."""
    if _table_exists(cr, BACKUP_TABLE):
        _logger.info(
            "account_bill_approval_migration: backup table %s already "
            "exists, keeping it untouched.", BACKUP_TABLE,
        )
        return
    cr.execute(
        "CREATE TABLE %s AS SELECT * FROM %s" % (BACKUP_TABLE, TABLE)
    )
    cr.execute("SELECT count(*) FROM %s" % BACKUP_TABLE)
    _logger.info(
        "account_bill_approval_migration: backed up %s rows to %s",
        cr.fetchone()[0], BACKUP_TABLE,
    )


def _add_columns(cr):
    """Add the columns the new module introduces."""
    additions = [
        ("company_id", "INTEGER REFERENCES res_company(id)"),
        ("date_rejected", "TIMESTAMP WITHOUT TIME ZONE"),
        ("rejected_by_id", "INTEGER REFERENCES res_users(id)"),
        ("reject_reason", "TEXT"),
    ]
    for column, definition in additions:
        if _column_exists(cr, TABLE, column):
            continue
        cr.execute(
            "ALTER TABLE %s ADD COLUMN %s %s" % (TABLE, column, definition)
        )
        _logger.info(
            "account_bill_approval_migration: added column %s", column
        )


def _backfill_company(cr):
    """Fill company_id from the related bill."""
    if not _column_exists(cr, TABLE, "company_id"):
        return
    cr.execute("""
        UPDATE bill_approval_user_line AS l
        SET company_id = m.company_id
        FROM account_move AS m
        WHERE m.id = l.move_id
          AND l.company_id IS NULL
    """)
    _logger.info(
        "account_bill_approval_migration: back-filled company_id on %s rows",
        cr.rowcount,
    )


def _transfer_ownership(cr):
    """Move ir_model_data ownership from the legacy to the new module.

    This is what keeps the table alive when the legacy module is
    uninstalled.
    """
    for model, name_pattern in OWNERSHIP_ROWS:
        if name_pattern.endswith("%"):
            cr.execute("""
                UPDATE ir_model_data
                SET module = %s
                WHERE module = %s
                  AND model = %s
                  AND name LIKE %s
            """, (NEW_MODULE, LEGACY_MODULE, model, name_pattern))
        else:
            cr.execute("""
                UPDATE ir_model_data
                SET module = %s
                WHERE module = %s
                  AND model = %s
                  AND name = %s
            """, (NEW_MODULE, LEGACY_MODULE, model, name_pattern))
        _logger.info(
            "account_bill_approval_migration: transferred %s %s row(s) "
            "(%s)", cr.rowcount, model, name_pattern,
        )
