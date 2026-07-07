# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MisBudgetTree(models.Model):
    _name = "mis.budget.tree"
    _description = "Budget Tree Configuration"
    _order = "name"
    _inherit = ["mail.thread"]

    name = fields.Char(string="Tree Name", required=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    tree_line_ids = fields.One2many(
        comodel_name="mis.budget.tree.line",
        inverse_name="tree_id",
        string="Tree Lines",
        copy=True,
    )
    active = fields.Boolean(default=True)

    def _expand_tree_to_items(self, budget):
        """Expand this tree into mis.budget.by.account.item records for a budget.

        Returns list of (tree_line, item) tuples for all created items.
        Traverses the tree hierarchically: leaves become items with accounts,
        nodes become items with auto-sum.
        """
        self.ensure_one()
        result = []

        # Process root-level lines (no parent in tree)
        root_lines = self.tree_line_ids.filtered(lambda l: not l.parent_id)

        for line in root_lines:
            result.extend(line._expand_to_items(budget))

        return result


class MisBudgetTreeLine(models.Model):
    _name = "mis.budget.tree.line"
    _description = "Budget Tree Line"
    _order = "sequence, id"
    _inherit = ["mail.thread"]

    name = fields.Char(string="Label", required=True, tracking=True)
    tree_id = fields.Many2one(
        comodel_name="mis.budget.tree",
        string="Budget Tree",
        required=True,
        ondelete="cascade",
    )
    parent_id = fields.Many2one(
        comodel_name="mis.budget.tree.line",
        string="Parent Node",
        ondelete="cascade",
        index=True,
    )
    child_ids = fields.One2many(
        comodel_name="mis.budget.tree.line",
        inverse_name="parent_id",
        string="Children",
    )
    sequence = fields.Integer(string="Sequence", default=10)
    is_leaf = fields.Boolean(
        string="Is Leaf",
        default=True,
        help="Leaves map to specific accounts. Nodes (non-leaves) auto-sum their children.",
    )
    account_mask = fields.Char(
        string="Account Mask",
        help="Comma-separated account code prefixes. "
             "Examples: '30,31' matches all accounts starting with 30 or 31. "
             "'5' matches all 5xxx accounts. "
             "Only used when is_leaf=True.",
    )
    account_ids = fields.Many2many(
        comodel_name="account.account",
        relation="mis_budget_tree_line_account_rel",
        column1="tree_line_id",
        column2="account_id",
        string="Specific Accounts",
        help="Manually selected accounts for this tree line. "
             "Takes precedence over account_mask.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="tree_id.company_id",
        store=True,
    )

    @api.constrains("is_leaf", "parent_id")
    def _check_leaf_parent(self):
        """Nodes cannot have an account mask or specific accounts."""
        for line in self:
            if not line.is_leaf:
                if line.account_mask:
                    raise ValidationError(_(
                        "Node '%s' cannot have an account mask. "
                        "Only leaf lines can have account masks.",
                        line.name,
                    ))
                if line.account_ids:
                    raise ValidationError(_(
                        "Node '%s' cannot have specific accounts. "
                        "Only leaf lines can have accounts assigned.",
                        line.name,
                    ))

    @api.constrains("parent_id")
    def _check_recursion(self):
        """Prevent circular parent references."""
        if not self._check_recursion():
            raise ValidationError(_(
                "You cannot create recursive tree structures."
            ))

    def _expand_account_mask(self):
        """Expand the account_mask into a recordset of account.account.

        Examples:
            "30,31" → all accounts with code starting with '30' or '31'
            "5"     → all accounts with code starting with '5'
            "40,41,42" → all 40xx, 41xx, and 42xx accounts
        """
        self.ensure_one()
        if not self.account_mask:
            return self.env["account.account"]

        prefixes = [
            p.strip() for p in self.account_mask.split(",") if p.strip()
        ]
        domain = [
            "|" if len(prefixes) > 1 else "",
        ]
        for i, prefix in enumerate(prefixes):
            if i == 0:
                domain.append(("code", "=like", f"{prefix}%"))
            else:
                domain.append(("code", "=like", f"{prefix}%"))

        # Clean up leading empty string operator if only one prefix
        if len(prefixes) == 1:
            domain = [("code", "=like", f"{prefixes[0]}%")]

        return self.env["account.account"].search(
            domain + [("deprecated", "=", False), ("company_id", "=", self.company_id.id)]
        )

    def get_accounts(self):
        """Return all account.account records for this tree line.

        Uses account_ids if set, otherwise expands account_mask.
        """
        self.ensure_one()
        if self.account_ids:
            return self.account_ids
        return self._expand_account_mask()

    def _expand_to_items(self, budget):
        """Recursively expand this tree line into budget items for a budget.

        Returns list of (tree_line, item) tuples.
        """
        self.ensure_one()
        result = []

        if self.is_leaf:
            # Leaf → create budget items for each matching account × period
            accounts = self.get_accounts()
            date_ranges = self._get_date_ranges_for_budget(budget)

            for account in accounts:
                for dr in date_ranges:
                    item = self._create_or_get_item(budget, account, dr)
                    result.append((self, item))

        else:
            # Node → create a node item first, then process children
            date_ranges = self._get_date_ranges_for_budget(budget)

            # Expand children
            for child in self.child_ids:
                result.extend(child._expand_to_items(budget))

        return result

    def _get_date_ranges_for_budget(self, budget):
        """Get date ranges that fit within the budget's date range."""
        # Use the budget's date_type if available
        date_type = None
        if hasattr(budget, "date_type") and budget.date_type:
            date_type = budget.date_type
        else:
            # Default to monthly ranges
            date_type = self.env["date.range.type"].search(
                [("name", "=like", "%mon%")], limit=1
            )
            if not date_type:
                date_type = self.env["date.range.type"].search([], limit=1)

        if date_type:
            return self.env["date.range"].search([
                ("type_id", "=", date_type.id),
                ("date_start", ">=", budget.date_from),
                ("date_end", "<=", budget.date_to),
            ])

        # Fallback: single period covering the whole budget
        return self.env["date.range"]

    def _create_or_get_item(self, budget, account, date_range):
        """Create or find an existing budget item for account+period combo."""
        item_model = self.env["mis.budget.by.account.item"]

        domain = [
            ("budget_id", "=", budget.id),
            ("account_id", "=", account.id),
        ]
        if date_range:
            domain.extend([
                ("date_range_id", "=", date_range.id),
                ("date_from", "=", date_range.date_start),
                ("date_to", "=", date_range.date_end),
            ])

        item = item_model.search(domain, limit=1)
        if not item:
            vals = {
                "name": account.name,
                "budget_id": budget.id,
                "account_id": account.id,
                "tree_line_id": self.id,
            }
            if date_range:
                vals.update({
                    "date_range_id": date_range.id,
                    "date_from": date_range.date_start,
                    "date_to": date_range.date_end,
                })
            item = item_model.create(vals)

        return item
