import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class AccountAnalyticPlan(models.Model):
    _inherit = 'account.analytic.plan'

    plan_replacement_id = fields.Many2one('account.analytic.plan', string='This plan is replaced by', copy=False)
    plan_replaces_id = fields.Many2one('account.analytic.plan', string='This plan replaces', copy=False)
    is_replaced = fields.Boolean(compute='_compute_is_replaced', store=True)

    @api.depends('plan_replacement_id', 'plan_replaces_id')
    def _compute_is_replaced(self):
        for plan in self:
            plan.is_replaced = bool(plan.plan_replacement_id or plan.plan_replaces_id)

    def action_replace_plan(self):
        return {
            'name': _('Replace Analytic Plan'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.replace.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_old_plan_id': self.id}
        }
