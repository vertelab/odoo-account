import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class AccountAnalyticReplaceWizard(models.TransientModel):
    _name = 'account.analytic.replace.wizard'
    _description = 'Analytic Plan Replace Wizard'

    old_plan_id = fields.Many2one('account.analytic.plan', string='Old Plan', required=True)
    new_plan_name = fields.Char(string='New Plan Name', required=True)
    copy_accounts = fields.Boolean(string='Copy All Analytic Accounts', default=True)
    new_plan_id = fields.Many2one('account.analytic.plan', string='New Plan')

    def action_replace(self):
        self.ensure_one()
        
        # Create new plan
        new_plan_vals = {
            'name': self.new_plan_name,
            'default_applicability': 'optional',  # or 'mandatory' based on old plan
        }
        new_plan = self.env['account.analytic.plan'].create(new_plan_vals)
        
        # Set old plan to unavailable and link replacement
        self.old_plan_id.write({
            'default_applicability': 'unavailable',
            'plan_replacement_id': new_plan.id,
        })
        new_plan.plan_replaces_id = self.old_plan_id
        
        # Copy analytic accounts if requested
        if self.copy_accounts:
            for old_account in self.old_plan_id.account_ids:
                new_account_vals = {
                    'name': old_account.name,
                    'plan_id': new_plan.id,
                    'code': old_account.code,
                    'company_id': old_account.company_id.id,
                    'partner_id': old_account.partner_id.id,
                    'replaces_account_id': old_account.id,
                }
                new_account = self.env['account.analytic.account'].create(new_account_vals)
                old_account.replacement_account_id = new_account
        
        self.new_plan_id = new_plan
        return {
        'type': 'ir.actions.act_window',
        'res_model': 'account.analytic.plan',
        'res_id': new_plan.id,
        'view_mode': 'form',
        'view_type': 'form',
        'target': 'current', 
        }

