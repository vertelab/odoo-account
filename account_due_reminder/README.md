# Account: Invoice Payment Reminder

Follow-up reminders for overdue customer invoices: payment plans with stepped
actions (print, e-mail) and the reminder lines generated from them.

## Where the menus live

| Menu | Model | Parent |
|---|---|---|
| Payment Reminder | `account.payment.plan` | Accounting → Customers |
| Follow-up Reminder | `payment.reminder.line` | Accounting → Customers |

Both are restricted to `account.group_account_manager`.

The menus used to hang under `account.account_invoicing_menu`
(Configuration → Invoicing), which is a settings menu — a poor home for the
day-to-day work of chasing unpaid invoices. They now sit under
`account.menu_finance_receivables`, next to the customer invoices they concern.

⚠ If you add a menu to this module, parent it under
`account.menu_finance_receivables`. `account_accountant_ce` hides
`account.menu_finance`, and anything parented there disappears from the UI.

## Version 18.0.1.1.0 — menu xmlid fix

Up to 18.0.1.0.0, `views/account_payment_plan_views.xml` and
`views/payment_reminder_line_views.xml` both declared
`id="account_payment_reminder_menu"`. The second file silently overwrote the
first, so only one menu existed.

From 18.0.1.1.0 the xmlids are `menu_account_payment_plan` and
`menu_payment_reminder_line`. `migrations/18.0.1.1.0/pre-migrate.py` removes
the leftover menu and its `ir.model.data` row, but only when the menu's action
is one of the two known ones — a reused xmlid is left alone.

## Features

- Automation: scheduled jobs `Account Report Followup` and `Execute followup`.
- Extends 4 views in the Odoo interface.
- Builds on `account.move`, `account.payment.plan`, `account.payment.term` and
  `mail.activity.type`.
