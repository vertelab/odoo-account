# Plan: Enterprise Reconciliation Features for OCA CE

## Problem

Enterprise `account_accountant` has rich bank reconciliation features that OCA's `account-reconcile` modules lack. The OCA modules provide a solid foundation but miss ~12 major feature areas.

## Goal

Create a CE module (`account_reconcile_enterprise_ce`) that extends OCA `account_reconcile_oca` with the missing enterprise reconciliation features, prioritizing the largest user-facing gaps.

## Gap Analysis (Enterprise vs OCA)

| # | Feature | Enterprise | OCA | Effort |
|---|---------|-----------|-----|--------|
| 1 | Multi-stage auto-reconciliation (CRON + 5-stage matching) | `_cron_try_auto_reconcile_statement_lines()` | `_auto_reconcile()` at create only | High |
| 2 | Rich kanban reconciliation UI with unfold/reveal | 30+ JS components, `BankReconciliationService` | ~10 JS files, separate form view | High |
| 3 | Smart partner retrieval (bank account + fuzzy name) | `_retrieve_partner()` with matching | Simple hook | Medium |
| 4 | Auto-creation of reconcile rules from patterns | `_check_and_create_reconciliation_rule()` | None | Medium |
| 5 | Reactive reconcile service/state management | `BankReconciliationService` | None | High |
| 6 | Outstanding credits/debits widget on invoices | Statement lines in payment widget | None | Medium |
| 7 | Auto-reconcile wizard (Perfect Match + Clear Account) | `account.auto.reconcile.wizard` | None | Low |
| 8 | Advanced manual reconcile wizard (taxes, lock date) | `account.reconcile.wizard` | Simpler wizard | Medium |
| 9 | Predictive account/tax/product from history | PostgreSQL tsvector | None | High |
| 10 | Deferred expense/revenue management | Separate deferred module | None | High (standalone) |
| 11 | Reconcile on account.move.form (reconcile button) | `action_reconcile` on move lines | None | Low |
| 12 | Dashboard integration (reconcile counts, to-review) | Dashboard extensions | None | Low |

## Architecture

### Module: `account_reconcile_enterprise_ce`

```
account_reconcile_enterprise_ce/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── account_bank_statement_line.py    # multi-stage reconcile, partner retrieval
│   ├── account_journal.py                # dashboard reconcile data
│   ├── account_move_line.py              # action_reconcile, outstanding widget
│   ├── account_reconcile_model.py        # pattern-based auto-creation
│   └── account_auto_reconcile_wizard.py  # Perfect Match / Clear Account
├── views/
│   ├── account_move_line.xml
│   ├── account_journal_dashboard.xml
│   └── account_auto_reconcile_wizard.xml
├── static/
│   └── src/
│       ├── js/                          # JS components (match if needed)
│       └── scss/
├── security/
│   └── ir.model.access.csv
├── data/
│   └── cron_data.xml
├── tests/
│   └── test_reconcile.py
└── docs/
```

Depends on: `account_reconcile_oca`, `account_statement_base`, `account_reconcile_model_oca`

## Implementation Phases

### Phase 1: Reconcile Button & Outstanding Widget (Low effort, high visibility)
- Add `action_reconcile` method on `account.move.line` → opens OCA reconcile wizard
- Add outstanding credits/debits column in invoice payment widget showing unmatched bank statement lines
- Add dashboard reconcile counts (extend `_get_journal_dashboard_data_batched`)

### Phase 2: Multi-Stage Auto-Reconciliation (High effort, critical)
Port enterprise's 5-stage matching for statement lines:
1. `end_to_end_id` exact match (statement_line ↔ payment_transaction)
2. Payment reference word matching (statement ref ↔ invoice ref)
3. Partner-based amount match (same partner, same amount +/- 3%)
4. Invoice/payment word matching (extract invoice numbers from refs)
5. Reconcile model application

Implement as CRON with batch processing, time limits, and configurable stage selection.

### Phase 3: Smart Partner Retrieval (Medium effort)
- Bank account number matching (IBAN/account from statement → partner bank accounts)
- Fuzzy name matching from statement partner_name
- Cache previously matched partners by bank account
- Expose as hook so OCA modules can customize

### Phase 4: Auto-Reconcile Wizard (Low effort)
- "Perfect Match" mode: Batch reconcile by end_to_end_id
- "Clear Account" mode: Reconcile all open items by amount/partner match
- Reuse OCA's existing reconcile model logic

### Phase 5: Pattern-Based Rule Creation (Medium effort)
- Track account assignments by counterpart for each partner
- When same counterpart assigned ≥3 times for same partner → auto-create reconcile model
- Notify accountant of newly created rules

### Phase 6: Auto-Rule Creation (Medium effort, optional)
- Track account assignments by counterpart for each partner
- When same counterpart assigned ≥3 times for same partner → auto-create reconcile model
- Notify accountant of newly created rules

## OCA Alignment Strategy

| Enterprise Feature | OCA Module to Extend | Approach |
|---|---|---|
| Auto-reconciliation | `account_reconcile_oca` | Override `_auto_reconcile()` + add CRON |
| Kanban UI | `account_reconcile_oca` | Extend existing reconcile views/JS |
| Partner retrieval | `account_reconcile_oca` | Override `_retrieve_partner()` |
| Rule auto-creation | `account_reconcile_model_oca` | New model with pattern tracking |
| Manual reconcile wizard | `account_manual_reconcile_wizard` | Extend with tax/lock-date support |
| Outstanding widget | `account_reconcile_oca` | New field on move.line |
| Predictive AI | Standalone module | PostgreSQL text search |

## Risk Assessment

- **JS complexity**: Enterprise bank rec widget is 30+ components. For CE, we should build incrementally — start with outstanding widget + manual reconcile improvements, add rich UI later.
- **Performance**: Multi-stage matching queries must be efficient (indexed fields, batch processing, time limits).
- **Upgrade compatibility**: All overrides should use `_super` calls and avoid monkey-patching.

## Success Criteria

1. Statement lines auto-reconcile with >=80% of enterprise matching accuracy
2. Outstanding credits/debits shown on invoices without JS rewrite
3. Dashboard shows reconcile counts
4. Reconcile rules created from patterns with notification
5. All OCA override tests pass

## Timeline Estimate

- Phase 1: 1-2 days
- Phase 2: 3-5 days
- Phase 3: 1-2 days
- Phase 4: 1 day
- Phase 5: 1-2 days
- Testing/Polish: 1-2 days
- **Total: ~8-14 days**
