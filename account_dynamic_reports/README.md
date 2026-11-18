# Accounting: Dynamic Reports

Dynamic accounting reports for Odoo CE — balance sheet, P&L, general ledger,
trial balance, aged receivable/payable and partner ledger — built on core's
`account.report` models instead of Enterprise `account_reports`.

## Where the menus live

| Menu | Parent |
|---|---|
| Dynamic Reports | Accounting → Reporting (`account.menu_finance_reports`) |
| Unrealized Currency Gains/Losses | Accounting → Reporting → Partner Reports |

⚠ **Do not parent a menu under `account.menu_finance`.** `account_accountant_ce`
hides that root menu by clearing its `web_icon`, so anything hanging there is
created but never rendered. This module's own Dynamic Reports menu sat there
until 18.0.1.6.4 and was invisible as a result.

Reports belong under `account.menu_finance_reports`.

## Features

- Balance sheet, P&L, general ledger, trial balance, aged receivable/payable,
  partner ledger.
- Drill-down with expand/collapse, date filters, comparison columns and XLSX
  export.
- Exposes HTTP endpoints for external systems.
- Builds on `account.currency.revaluation.report.handler` and `account.report`.

## Version 18.0.1.6.4

`menu_dynamic_reports` moved from `account.menu_finance` to
`account.menu_finance_reports`. No data changes — only the menu's parent.
