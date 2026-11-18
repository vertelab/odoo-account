# Account: Accounting UI (CE)

Community accounting UI adjustments: the app reads as "Accounting" instead of
"Invoicing", and Community-only fields are exposed where Enterprise shows them.

## Menu ownership — where a menu may hang

This module owns its own root menu `menu_accounting` and hides core's
`account.menu_finance` by clearing its `web_icon`. A root menu without an icon
is not shown in the app switcher, so everything still parented to
`account.menu_finance` becomes invisible with it.

`data/account_accountant_data.xml` reparents a fixed list of menus onto
`menu_accounting`. **Any new menu must hang under one of those parents** — never
directly under `account.menu_finance`:

| Function | Parent |
|---|---|
| Reports, statements, MIS | `account.menu_finance_reports` |
| Customer invoices, payments, follow-up | `account.menu_finance_receivables` |
| Vendor bills, payments | `account.menu_finance_payables` |
| Journal entries, periods | `account.menu_finance_entries` |
| Settings, chart of accounts, journals | `account.menu_finance_configuration` |

### Detection

`hooks.py` runs `check_hidden_root_menus` on every registry load (`post_load`)
and logs a warning for every menu still hanging under `account.menu_finance`:

```
account_accountant_ce: menu account_dynamic_reports.menu_x ('X') hangs under
the hidden account.menu_finance and will not be visible. Parent it under
account.menu_finance_reports (reports) or account.menu_finance_receivables
(customer follow-up) instead.
```

The check warns rather than fails: a placement mistake should not make a
third-party module uninstallable.

## What this module does

- Renames the accounting app category from "Invoicing" to "Accounting".
- Renames the top-level menu from "Invoicing" to "Accounting" by owning a new
  root menu and reparenting every account sub-menu onto it.
- Renames the settings app title from "Invoicing" to "Accounting".
- Shows "Allow Reconciliation" (`reconcile`) on the account form.
- Shows the inalterability hash (`inalterable_hash`) on journal entries for
  developers (`base.group_no_one`).
- Restricts the partner accounting entries group to
  `account.group_account_basic`.

## What this module does NOT do

- It owns no models and adds no business logic; it is a pure UI module. Fiscal
  year management lives in `account_fiscal_year_vrtl`.
- It does not redefine any `account` group. Community's group architecture
  (`account/security/account_security.xml`) is left untouched.

## Dependencies

- `account_asset_management`
  (https://github.com/OCA/account-financial-tools)
