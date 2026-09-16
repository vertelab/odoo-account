# Vendor Bill Approval

Approve vendor bills before they can be posted, with **freely selectable
approvers**.

## Why

The legacy Linserv module (`purchase_vendor_bill_approval`) limited the
approver field to users pre-configured on the vendor, and to members of a
single hidden group. In practice the approver varies per bill, so the field
must be selectable at registration time (T/11311).

## Features

- **Freely selectable approvers** — any user can be added to a bill; the
  vendor's list is only a *suggestion*.
- **Approve / reject** — rejection requires a reason and reopens the bill
  ("reject and reopen"). The rejecting user cannot approve the same line
  again; a new line has to be added.
- **Posting guard** — a vendor bill cannot be posted while approvals are
  outstanding.
- **Systray pen** — shows how many bills are waiting for *your* approval.
- **Multi-company** — `company_id` is stored on every approval line.
- **Chatter trail** — every request, approval and rejection is logged with
  the reason.
## Groups

| Group | Purpose |
|---|---|
| `group_bill_approval_user` | Can be assigned as approver, approve/reject |
| `group_bill_approval_readonly` | Sees approval status, cannot act |
| `group_bill_approval_manager` | Configures default approvers per vendor |

`group_bill_approval_manager` implies `group_bill_approval_user`.
`account.group_account_manager` implies `group_bill_approval_manager`.

## Configuration

1. Set **Default Bill Approvers** on the vendor (Accounting tab). This is a
   suggestion only.
2. On the bill, open the **Approvers** tab and add or remove approvers.
3. Click **Request Approval** to notify them.
4. Each approver clicks **Approve Bill** (or **Reject**).
5. Once all lines are approved, the bill can be posted.

## Model compatibility

The model `bill.approval.user.line` and the field names
`approving_user_ids` / `bill_approving_user_ids` are kept identical to the
legacy Linserv module, so existing data can be reused. See
`account_bill_approval_migration` for the ownership hand-over.

## License

AGPL-3. Copyright 2026 Vertel AB.
