#!/usr/bin/env bash
#
# 3-way match migration runbook (EE -> CE, legacy bridge -> AI)
#
# Migrerar en Odoo-databas från Enterprise-modulen `account_3way_match`
# (OEEL-1) och/eller den legacy-baserade bryggan
# `account_invoice_ai_3way_match` till Vertels rena
# `account_3way_match_ce` + `account_3way_match_ai`.
#
# VIKTIGT — ORDNINGEN ÄR OBLIGATORISK:
#   CE måste installeras INNAN EE avinstalleras. Om EE avinstalleras först
#   droppar Odoo kolumnerna release_to_pay/can_be_paid och ALLA värden
#   nollställs till 'exception' (bevisat 2026-10-08).
#
# Användning:
#   ./3way_match_migrate.sh --db <databas> [--odoo-config <fil>] [--dry-run]
#
# Steg:
#   1. Inventera (räkna tillstånd före)
#   2. Databasdump (referens)
#   3. Installera account_3way_match_ce (medan EE är kvar)
#   4. Avinstallera account_3way_match (EE)
#   5. Verifiera att tillståndsdata är bevarad
#   6. (Valfritt) installera account_3way_match_ai + avveckla legacy AI-bas
#
set -euo pipefail

DB=""
ODOO_CONFIG="/etc/odoo/odoo.conf"
DRY_RUN=0
ODOO_BIN="${ODOO_BIN:-odoo}"
PSQL="psql"

usage() {
  grep '^#' "$0" | sed 's/^# \{0,1\}//'
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --db) DB="$2"; shift 2 ;;
    --odoo-config) ODOO_CONFIG="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage ;;
    *) echo "Okänt argument: $1" >&2; usage ;;
  esac
done

[[ -n "$DB" ]] || { echo "Fel: --db krävs" >&2; usage; }

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  [dry-run] $*"
  else
    echo "  \$ $*"
    "$@"
  fi
}

odoo_run() {
  run sudo -u odoo "$ODOO_BIN" --config "$ODOO_CONFIG" -d "$DB" "$@"
}

count_states() {
  # Skriv ut antal fakturor per release_to_pay och force-flaggor.
  sudo -u postgres "$PSQL" -d "$DB" -tAc \
    "SELECT COALESCE(release_to_pay,'(null)'), COUNT(*) FROM account_move GROUP BY 1 ORDER BY 1;"
  echo "force_release_to_pay=True: $(sudo -u postgres "$PSQL" -d "$DB" -tAc \
    "SELECT COUNT(*) FROM account_move WHERE force_release_to_pay = true;")"
}

module_state() {
  sudo -u postgres "$PSQL" -d "$DB" -tAc \
    "SELECT state FROM ir_module_module WHERE name='$1';" 2>/dev/null || echo "missing"
}

echo "=== 3-way match migration: $DB ==="
echo

echo "--- 1. Inventering ---"
EE_STATE="$(module_state account_3way_match)"
CE_STATE="$(module_state account_3way_match_ce)"
BRIDGE_STATE="$(module_state account_invoice_ai_3way_match)"
AI_STATE="$(module_state account_3way_match_ai)"
echo "  account_3way_match (EE):         ${EE_STATE:-missing}"
echo "  account_3way_match_ce:           ${CE_STATE:-missing}"
echo "  account_invoice_ai_3way_match:   ${BRIDGE_STATE:-missing}"
echo "  account_3way_match_ai:           ${AI_STATE:-missing}"
echo
echo "  Tillstånd FÖRE:"
count_states | sed 's/^/    /'
echo

if [[ "$EE_STATE" != "installed" && "$CE_STATE" != "installed" ]]; then
  echo "Ingen 3-vägsmatchningsmodul installerad — inget att migrera."
  exit 0
fi

echo "--- 2. Databasdump (referens) ---"
# sudoers tillåter NOPASSWD för psql/createdb/dropdb men inte pg_dump.
# Använd en template-klon som snapshot (kräver inga aktiva sessioner).
SNAP="${DB}_3way_snap_$(date +%Y%m%d%H%M%S)"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "  [dry-run] sudo -u postgres createdb -O odoo -T $DB $SNAP"
else
  if sudo -n -u postgres createdb -O odoo -T "$DB" "$SNAP" 2>/dev/null; then
    echo "  snapshot: $SNAP (template-klon)"
  else
    echo "  VARNING: kunde inte skapa snapshot (aktiva sessioner?)."
    echo "  Gör en dump manuellt innan du fortsätter:"
    echo "    sudo -u postgres pg_dump -Fc $DB -f /tmp/${DB}_3way.dump"
  fi
fi
echo

if [[ "$EE_STATE" == "installed" && "$CE_STATE" != "installed" ]]; then
  echo "--- 3. Installera account_3way_match_ce (INNAN EE avinstalleras) ---"
  odoo_run -i account_3way_match_ce --stop-after-init
  echo
  echo "--- 4. Avinstallera account_3way_match (EE) ---"
  # Odoo CLI kan inte avinstallera; kör via shell.
  run sudo -u odoo "$ODOO_BIN" shell --config "$ODOO_CONFIG" -d "$DB" --no-http <<'PYEOF'
ee = env['ir.module.module'].search([('name', '=', 'account_3way_match')])
if ee.state == 'installed':
    ee.button_immediate_uninstall()
    env.cr.commit()
print("EE state:", env['ir.module.module'].search([('name', '=', 'account_3way_match')]).state)
PYEOF
  echo
elif [[ "$CE_STATE" == "installed" ]]; then
  echo "--- 3-4. CE redan installerad — uppgradera på plats ---"
  odoo_run -u account_3way_match_ce --stop-after-init
  echo
fi

echo "--- 5. Verifiera att tillståndsdata är bevarad ---"
echo "  Tillstånd EFTER:"
count_states | sed 's/^/    /'
echo
echo "  Jämför med 'FÖRE' ovan. Antalen per tillstånd ska vara oförändrade."
if [[ "$DRY_RUN" -eq 0 && -n "${SNAP:-}" ]]; then
  echo "  Vid avvikelse: återställ från snapshoten med"
  echo "    sudo -u postgres psql -c 'DROP DATABASE $DB;'"
  echo "    sudo -u postgres createdb -O odoo -T $SNAP $DB"
fi
echo

echo "--- 6. AI-matchningsmodulen (valfritt) ---"
if [[ "$AI_STATE" != "installed" ]]; then
  echo "  Installera account_3way_match_ai kräver ai_agent_core och att"
  echo "  legacy ai_agent inte är installerad (de kan inte samexistera)."
  echo "  Kör manuellt när AI-baskonflikten är löst för kunden:"
  echo "    odoo -c $ODOO_CONFIG -d $DB -i account_3way_match_ai --stop-after-init"
else
  echo "  account_3way_match_ai redan installerad."
fi
echo

echo "=== Klart ==="
