# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date


class MisBudgetTreeCreateWizard(models.TransientModel):
    _name = "mis.budget.tree.create.wizard"
    _description = "Create Budget from Tree"

    tree_id = fields.Many2one(
        comodel_name="mis.budget.tree",
        string="Budget Tree",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(
        string="Budget Name",
        required=True,
        default=lambda self: _("Budget %s") % date.today().strftime("%Y"),
    )
    date_from = fields.Date(
        string="Start Date",
        required=True,
        default=lambda self: date(date.today().year, 1, 1),
    )
    date_to = fields.Date(
        string="End Date",
        required=True,
        default=lambda self: date(date.today().year, 12, 31),
    )
    is_forecast = fields.Boolean(
        string="Create as Forecast",
        default=False,
        help="If enabled, the budget will be created as a dynamic forecast.",
    )
    forecast_cutoff_date = fields.Date(
        string="Forecast Cutoff",
        default=lambda self: date.today(),
    )
    date_type_id = fields.Many2one(
        comodel_name="date.range.type",
        string="Period Type",
        required=True,
        default=lambda self: self.env["date.range.type"].search(
            [("name", "like", "%mon%")], limit=1
        )
        or self.env["date.range.type"].search([], limit=1),
    )

    def action_create_budget(self):
        """Create a mis.budget.by.account from the selected tree."""
        self.ensure_one()

        # Create the budget header
        budget_vals = {
            "name": self.name,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "is_forecast": self.is_forecast,
            "forecast_cutoff_date": self.forecast_cutoff_date if self.is_forecast else False,
        }
        if hasattr(self.env["mis.budget.by.account"], "date_type"):
            budget_vals["date_type"] = self.date_type_id.id

        budget = self.env["mis.budget.by.account"].create(budget_vals)

        # Expand the tree into budget items
        self.tree_id._expand_tree_to_items(budget)

        # Build the hierarchy: create parent-child relationships
        # between items based on the tree structure
        self._build_item_hierarchy(budget)

        # Redirect to the new budget
        return {
            "type": "ir.actions.act_window",
            "name": budget.name,
            "res_model": "mis.budget.by.account",
            "view_mode": "form",
            "res_id": budget.id,
        }

    def _build_item_hierarchy(self, budget):
        """Build parent-child relationships between budget items.

        Traverses the tree recursively: for each non-leaf tree line,
        creates a parent budget item and links its children.
        """
        # Map tree_line → budget_item
        item_model = self.env["mis.budget.by.account.item"]
        items = item_model.search([("budget_id", "=", budget.id)])

        # Build a lookup: tree_line_id → item(s)
        tree_to_items = {}
        for item in items:
            if item.tree_line_id:
                tid = item.tree_line_id.id
                if tid not in tree_to_items:
                    tree_to_items[tid] = []
                tree_to_items[tid].append(item)

        # Create node items for non-leaf tree lines
        def process_tree_line(tree_line):
            """Recursively create node items and link children."""
            if tree_line.is_leaf:
                return  # Leaves are already created

            # Create a node item for this tree line
            # Get date ranges from existing items
            existing_items = items.filtered(
                lambda i: i.tree_line_id and i.tree_line_id.id in [
                    c.id for c in tree_line.child_ids
                ]
            )
            # Use unique date ranges from children
            date_keys = set()
            for ei in existing_items:
                key = (ei.date_from, ei.date_to)
                if key not in date_keys:
                    date_keys.add(key)
                    item_model.create({
                        "name": tree_line.name,
                        "budget_id": budget.id,
                        "tree_line_id": tree_line.id,
                        "is_node": True,
                        "date_from": ei.date_from,
                        "date_to": ei.date_to,
                        "date_range_id": ei.date_range_id.id if ei.date_range_id else False,
                        "account_id": False,
                    })

            # Process children
            for child in tree_line.child_ids:
                process_tree_line(child)

        # Process all root-level tree lines
        for line in self.tree_id.tree_line_ids.filtered(lambda l: not l.parent_id):
            process_tree_line(line)

        # Now link parent-child items: for each tree line that has a parent,
        # find the corresponding budget items and set parent_id
        for tree_line in self.tree_id.tree_line_ids.filtered("parent_id"):
            if tree_line.parent_id.id not in tree_to_items:
                continue
            if tree_line.id not in tree_to_items:
                continue

            parent_items = tree_to_items[tree_line.parent_id.id]
            child_items = tree_to_items[tree_line.id]

            # Match parent and child items by date range
            for parent_item in parent_items:
                for child_item in child_items:
                    if (parent_item.date_from == child_item.date_from
                            and parent_item.date_to == child_item.date_to):
                        child_item.parent_id = parent_item.id
