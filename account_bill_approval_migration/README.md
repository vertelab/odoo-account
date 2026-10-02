# Vendor Bill Approval — Migration

**One-shot migration module. Uninstall it once the migration is verified.**

## What it does

Moves the existing vendor-bill approval data from the legacy Linserv module
`purchase_vendor_bill_approval` to `account_bill_approval`.

The legacy module owns the `ir.model` record for
`bill.approval.user.line`. When it is uninstalled Odoo runs
`DROP TABLE bill_approval_user_line CASCADE` — the approval history would be
lost even though the new module declares the same model.

This module makes the new module the owner instead, so the table survives
the uninstall.

## Steps

1. **Backup** — `bill_approval_user_line` is copied to
   `bill_approval_user_line_backup`. An existing backup is never
   overwritten.
2. **Add columns** — `company_id`, `date_rejected`, `rejected_by_id`,
   `reject_reason`.
3. **Back-fill** — `company_id` is filled from the related `account.move`.
4. **Transfer ownership** — `ir_model_data` rows for the model, its fields,
   its selections and its access rules are re-pointed from
   `purchase_vendor_bill_approval` to `account_bill_approval`.

The hook is idempotent: re-running it changes nothing.

## Deployment order

```
1. Install account_bill_approval + account_bill_approval_migration
2. Verify: row count, company_id filled, backup table present
3. Uninstall purchase_vendor_bill_approval
4. Verify: row count UNCHANGED          <-- the critical test
5. Uninstall account_bill_approval_migration
```

**Never uninstall the legacy module before step 3.**

## Why step 3 is not optional

Until the legacy module is uninstalled the interface is broken, even though
the data is safe. Both modules declare the model
`bill.approval.user.line` with `_name`, and Odoo keeps exactly **one**
registry class per model name: the class of the module loaded last replaces
the other one entirely (a class that sets `_name` without listing it in
`_inherit` replaces the existing class instead of extending it). Modules are
loaded in name order, so `purchase_vendor_bill_approval` is loaded after
`account_bill_approval` and wins.

The running model then loses `date_rejected`, `company_id`,
`rejected_by_id`, `reject_reason` and `ret_bill_approval_count` while the
database table and the views still use them. The vendor bill form fails in
the browser with:

```
Caused by: Error: "bill.approval.user.line"."date_rejected" field is undefined.
```

and the systray pen logs `The method
'bill.approval.user.line.ret_bill_approval_count' does not exist`.

`account_bill_approval` therefore refuses to install while the legacy module
is installed without this bridge (`pre_init_hook`) and logs a critical error
if the combination is already in place (`post_init_hook`).

## Cleanup

The backup table `bill_approval_user_line_backup` is intentionally left
behind. Drop it manually once the migration is verified in every
environment:

```sql
DROP TABLE bill_approval_user_line_backup;
```

## License

AGPL-3. Copyright 2026 Vertel AB.
