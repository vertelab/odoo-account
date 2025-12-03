import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.osv import expression


_logger = logging.getLogger(__name__)

class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    replacement_account_id = fields.Many2one('account.analytic.account', string='This account is replaced by', copy=False)
    replaces_account_id = fields.Many2one('account.analytic.account', string='This account replaces', copy=False)
    plan_replacement_id = fields.Many2one('account.analytic.plan', string='Plan Replacement', related='plan_id.plan_replacement_id', store=True)

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = args or []
        if not name:
            return super().name_search(name=name, args=args, operator=operator, limit=limit)
        
        domain = ['|',
                  ('name', operator, name),
                  ('replaces_account_id.name', operator, name)]
        domain = expression.AND([args, domain])
        records = self.search(domain, limit=limit)
        _logger.warning("name_search called, found %d records", len(records))
        return [(rec.id, rec.display_name or "") for rec in records]



    @api.depends('code', 'partner_id')
    def _compute_display_name(self):
        for analytic in self:
            name = analytic.name
            if analytic.code:
                name = f'[{analytic.code}] {name}'
            if analytic.partner_id.commercial_partner_id.name:
                name = f'{name} - {analytic.partner_id.commercial_partner_id.name}'
            if analytic.replaces_account_id:
                name = f'{name} - Replacment for {analytic.replaces_account_id.name}' 
            analytic.display_name = name
