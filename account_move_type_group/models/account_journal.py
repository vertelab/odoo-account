from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # Odoo 18 owns `account.journal.group` (the multi-ledger filter) and
    # `account.journal.journal_group_ids`. Naming this field `group_id` as the
    # 16.0 module did would collide with that model. `move_type_group_id` is a
    # res.groups record: journals in the same group are visible only to the
    # users of that group.
    move_type_group_id = fields.Many2one("res.groups", string="Journal Group")
