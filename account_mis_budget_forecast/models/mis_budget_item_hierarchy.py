# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MisBudgetByAccountItem(models.Model):
    _inherit = "mis.budget.by.account.item"

    parent_id = fields.Many2one(
        comodel_name="mis.budget.by.account.item",
        string="Parent Item",
        ondelete="cascade",
        index=True,
        help="Parent node in the budget hierarchy. Child amounts auto-sum into the parent.",
    )
    child_ids = fields.One2many(
        comodel_name="mis.budget.by.account.item",
        inverse_name="parent_id",
        string="Child Items",
    )
    tree_line_id = fields.Many2one(
        comodel_name="mis.budget.tree.line",
        string="Tree Line",
        ondelete="set null",
        index=True,
        help="The budget tree line that generated this item.",
    )
    is_node = fields.Boolean(
        string="Is Node",
        compute="_compute_is_node",
        store=True,
        help="Nodes are automatically computed from their children and are read-only.",
    )
    hierarchical_balance = fields.Monetary(
        string="Hierarchical Balance",
        compute="_compute_hierarchical_balance",
        store=True,
        currency_field="company_currency_id",
        help="For nodes: sum of children's balances. For leaves: own balance.",
    )
    hierarchical_forecast = fields.Monetary(
        string="Hierarchical Forecast",
        compute="_compute_hierarchical_forecast",
        store=True,
        currency_field="company_currency_id",
        help="For nodes in forecast mode: sum of children's forecast amounts.",
    )

    @api.depends("child_ids")
    def _compute_is_node(self):
        for rec in self:
            rec.is_node = bool(rec.child_ids)

    @api.depends(
        "is_node",
        "child_ids.balance",
        "child_ids.hierarchical_balance",
    )
    def _compute_hierarchical_balance(self):
        """
        Noder: summera barnens hierarchical_balance.
        Löv: använd egen balance.

        Inspirerad av Visma.nets budget tree auto-sum.
        """
        for rec in self:
            if rec.is_node:
                rec.hierarchical_balance = sum(
                    rec.child_ids.mapped("hierarchical_balance")
                )
            else:
                rec.hierarchical_balance = rec.balance

    @api.depends(
        "is_node",
        "child_ids.forecast_amount",
        "child_ids.hierarchical_forecast",
    )
    def _compute_hierarchical_forecast(self):
        """
        Noder i prognos-läge: summera barnens hierarchical_forecast.
        Löv: använd egen forecast_amount.
        """
        for rec in self:
            if rec.is_node:
                rec.hierarchical_forecast = sum(
                    rec.child_ids.mapped("hierarchical_forecast")
                )
            else:
                rec.hierarchical_forecast = rec.forecast_amount

    @api.constrains("parent_id")
    def _check_parent_recursion(self):
        """Prevent circular parent references on items."""
        if not self._check_recursion():
            from odoo.exceptions import ValidationError
            from odoo import _
            raise ValidationError(_(
                "You cannot create recursive budget item hierarchies."
            ))

    def action_view_children(self):
        """Open the children of this node item."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.name,
            "res_model": "mis.budget.by.account.item",
            "view_mode": "tree,form",
            "domain": [("parent_id", "=", self.id)],
            "context": {"default_parent_id": self.id},
        }
