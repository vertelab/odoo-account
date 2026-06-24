# Account Reconcile Enhanced

Enhanced reconciliation features for the OCA reconciliation stack
(`account_reconcile_oca` + `account_reconcile_model_oca`).

## What This Module Adds

### 1. Enhanced Reconciliation Wizard (`account.reconcile.wizard`)

| Feature | Description |
|---------|-------------|
| **Multi-account transfer** | Auto-detect and handle transfers between 2 different accounts |
| **Tax-aware write-offs** | Compute taxes (VAT/GST) on write-off lines |
| **Edit mode** | Single-line write-off with editable amount |
| **Allow partials** | Keep lines open after partial reconciliation |
| **Lock date validation** | Warning if reconciliation date violates fiscal lock dates |
| **Reconcile model autocomplete** | Smart reconciliation model suggestions |
| **Partner-aware transfers** | Transfers preserve partner ledger integrity |

### 2. Auto-Reconcile Wizard (`account.auto.reconcile.wizard`)

| Mode | Description |
|------|-------------|
| **Perfect Match** | Reconcile items with exact opposite balance (same account/partner/currency) |
| **Clear Account** | Reconcile all items when total balance = 0 in a group |

### 3. Enhanced Reconciliation Models

| Feature | Description |
|---------|-------------|
| `amount_type = 'regex'` | Extract counterpart amounts via regex from bank statement text |
| `amount_type = 'percentage_st_line'` | Amount as percentage of statement line |
| `get_available_reconcile_model_per_statement_line()` | SQL-optimized model matching per bank line |
| `_apply_reconcile_models()` | Auto-apply models on create/write/archive |
| `_trigger_reconciliation_model()` | Manual trigger with activity scheduling |
| `created_automatically` | Track auto-created reconciliation models |
| `next_activity_type_id` | Schedule follow-up activities after reconciliation |
| `reconcile_model_id` on move.line | Track which model created each journal item |

## How It Compares

### OCA Base (`account_reconcile_oca` + `account_reconcile_model_oca`)
- Modern reconciliation UI with `account.reconcile.abstract`
- Invoice matching with token-based text search
- Partner mapping, payment tolerance, early payment discount
- Write-off suggestion and manual reconciliation

### This Module (`account_reconcile_enhanced`)
- ✅ Multi-account transfer wizard
- ✅ Tax computation on write-offs
- ✅ Edit mode for single lines
- ✅ Auto-reconcile batch wizard
- ✅ SQL-optimized model matching
- ✅ Regex amount extraction
- ✅ Model auto-trigger on create/update
- ✅ Activity scheduling after reconciliation
- ✅ Built on OCA's modern reconciliation architecture
- ✅ AGPL licensed
- ✅ Works with OCA's `account_reconcile_oca` UI
- ✅ Excludes `account_accountant` to avoid conflicts

## Dependencies

- `account_reconcile_oca` (OCA)
- `account_reconcile_model_oca` (OCA)
- `account_reconcile_wizard` (OCA)

## Installation

```bash
# Place in your Odoo addons path alongside OCA account-reconcile modules
cd /path/to/odoo/addons
git clone https://github.com/OCA/account-reconcile.git
# This module lives in odoo-account repo:
# /usr/share/odoo-account/account_reconcile_enhanced/
```

## Usage

### Reconciliation Wizard
1. Select journal items from the reconciliation view
2. Click **Action > Reconcile Entries**
3. If 2 different accounts: review transfer info, set journal/date
4. If write-off needed: select account, partner, label, tax
5. Click **Reconcile** (or **Partial Reconcile** if keeping open)

### Auto-Reconcile
1. Go to **Accounting > Actions > Auto-reconcile**
2. Choose mode: **Perfect Match** or **Clear Account**
3. Set filters (date range, accounts, partners)
4. Click **Reconcile**

### Regex Amount Extraction
When creating reconciliation models, use `amount_type = 'regex'` with
a pattern that captures the amount in the first group:
```
Fee: ([0-9,.]+)
```

### Bank Fee Detection
Automatically detects and reconciles bank charges on incoming deposits.

**How it works:**
1. When a deposit statement line is partially matched, a small residual remains
2. If the residual is below the configured fee threshold, a bank fee model triggers
3. The fee is booked as a write-off to the configured expense account

**Setup:**
1. Go to **Accounting > Configuration > Reconciliation Models**
2. Create or edit a model, set **rule type** to "Write-off Suggestion"
3. Enable **Bank Fee Model** checkbox
4. Set **Fee Threshold (%)** — default 3% (residual < ~2.91% of original triggers it)
5. Configure the model line with your bank charges account (e.g., 07xxx)

**Default fee models included:**
- Bank Transaction Fee (3% threshold, match "fee")
- International Transfer Fee (5% threshold, match "intl fee")
- Card Processing Fee (5% threshold, match "processing")
- Bank Fee Auto-detect (2% threshold, catch-all)

**Fee detection formula:**
```
ABS(amount_residual) < (threshold / 100) * amount / (1 + threshold / 100)
```
Example: $100 deposit, 3% threshold → triggers when residual < $2.91

## License

AGPL-3.0
