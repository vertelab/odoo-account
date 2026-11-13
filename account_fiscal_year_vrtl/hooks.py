import logging

_logger = logging.getLogger(__name__)


def _migrate_from_account_period_vrtl(env):
    """Migration hook: convert existing account_period_vrtl data to new format.

    Converts:
    - account.period records → date.range + account.period (with _inherits)
    - account.fiscalyear → account.fiscal.year (remap fields)
    - Drops period_id column from account_move and account_move_line

    This hook is idempotent — it only runs if old data exists.
    """
    _logger.info("Starting migration from account_period_vrtl...")

    # Check if old module was installed
    if not env["ir.module.module"].search([
        ("name", "=", "account_period_vrtl"),
        ("state", "=", "installed"),
    ]):
        _logger.info("account_period_vrtl not installed — skipping migration")
        return

    # 1. Migrate fiscal years: account.fiscalyear → account.fiscal.year
    #
    # FIX 2026-10-30: `env["account.fiscalyear"]` no longer resolves once
    # account_period_vrtl is uninstalled or not installable — the model is
    # gone from the registry and env[...] raises KeyError. Guard on the
    # registry instead, so the hook is safe to run in either order.
    if "account.fiscalyear" not in env:
        _logger.info(
            "account.fiscalyear model not in registry — nothing to migrate")
        return

    old_fiscalyears = env["account.fiscalyear"].search([])
    _logger.info("Migrating %d fiscal years...", len(old_fiscalyears))

    for fy in old_fiscalyears:
        # Check if already migrated
        existing = env["account.fiscal.year"].search([
            ("name", "=", fy.name),
            ("company_id", "=", fy.company_id.id),
        ])
        if existing:
            _logger.info("Fiscal year '%s' already migrated — skipping", fy.name)
            continue

        env["account.fiscal.year"].create({
            "name": fy.name,
            "date_from": fy.date_start,
            "date_to": fy.date_stop,
            "company_id": fy.company_id.id,
        })
        _logger.info("Migrated fiscal year: %s", fy.name)

    # 2. Migrate periods: create date_range for each account.period
    old_periods = env["account.period"].search([])
    _logger.info("Migrating %d periods...", len(old_periods))

    for period in old_periods:
        # Check if already has a date_range
        if hasattr(period, "date_range_id") and period.date_range_id:
            _logger.info("Period '%s' already has date_range — skipping", period.name)
            continue

        date_range = env["date.range"].create({
            "name": period.name,
            "date_start": period.date_start,
            "date_end": period.date_stop,
            "company_id": period.company_id.id,
            "type_id": period.fiscalyear_id.date_range_type_id.id if hasattr(period.fiscalyear_id, "date_range_type_id") and period.fiscalyear_id.date_range_type_id else False,
        })
        period.date_range_id = date_range.id
        _logger.info("Migrated period: %s → date_range %s", period.name, date_range.name)

    # 3. Drop period_id from account_move (if column exists)
    # This is done via SQL since the field will be removed from the model
    try:
        env.cr.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'account_move'
                    AND column_name = 'period_id'
                ) THEN
                    ALTER TABLE account_move DROP COLUMN period_id;
                END IF;
            END $$;
        """)
        _logger.info("Dropped period_id column from account_move")
    except Exception as e:
        _logger.warning("Could not drop period_id from account_move: %s", e)

    # Drop period_id from account_move_line
    try:
        env.cr.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'account_move_line'
                    AND column_name = 'period_id'
                ) THEN
                    ALTER TABLE account_move_line DROP COLUMN period_id;
                END IF;
            END $$;
        """)
        _logger.info("Dropped period_id column from account_move_line")
    except Exception as e:
        _logger.warning("Could not drop period_id from account_move_line: %s", e)

    # Drop fiscalyear_id from account_move_line
    try:
        env.cr.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'account_move_line'
                    AND column_name = 'fiscalyear_id'
                ) THEN
                    ALTER TABLE account_move_line DROP COLUMN fiscalyear_id;
                END IF;
            END $$;
        """)
        _logger.info("Dropped fiscalyear_id column from account_move_line")
    except Exception as e:
        _logger.warning("Could not drop fiscalyear_id from account_move_line: %s", e)

    _logger.info("Migration from account_period_vrtl complete")


# ---------------------------------------------------------------------------
# Date range types: ownership and generation
#
# This module owns the Fiscal Year and Month types. l10n_se_date_ranges owns
# Quarter and Week and depends on this module. Each module generates the
# ranges for the types it owns, so neither has to call into the other.
# ---------------------------------------------------------------------------

def _generate_fiscal_year_ranges(env):
    """post_init_hook: generate Fiscal Year ranges for the surrounding years.

    Previous, current and next year, so a fresh install has periods to close
    immediately. Idempotent: a year that already has ranges is skipped.
    """
    from datetime import date

    date_range_type = env.ref(
        "account_fiscal_year_vrtl.date_range_type_fiscalyear",
        raise_if_not_found=False,
    )
    if not date_range_type:
        _logger.warning(
            "date_range_type_fiscalyear not found — skipping range generation.")
        return

    current_year = date.today().year
    for year in (current_year - 1, current_year, current_year + 1):
        existing = env["date.range"].search_count([
            ("type_id", "=", date_range_type.id),
            ("date_start", ">=", f"{year}-01-01"),
            ("date_start", "<=", f"{year}-12-31"),
        ])
        if existing:
            _logger.info(
                "Skipping Fiscal Year generation for %s (%d ranges already exist).",
                year, existing,
            )
            continue

        generator = env["date.range.generator"].create({
            "type_id": date_range_type.id,
            "date_start": date(year, 1, 1),
            "date_end": date(year, 12, 31),
            "name_expr": date_range_type.name_expr,
            "duration_count": date_range_type.duration_count,
            "unit_of_time": date_range_type.unit_of_time,
            "count": 0,
        })
        generator.action_apply()
        _logger.info("Generated Fiscal Year ranges for %s.", year)


def _post_init(env):
    """post_init_hook: run the legacy migration, then generate ranges."""
    _migrate_from_account_period_vrtl(env)
    _generate_fiscal_year_ranges(env)
