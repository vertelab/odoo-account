from odoo import models, fields, api, _


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    group_id = fields.Many2one('res.groups', string="Group")

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        # Add domain to filter by user's groups
        user_group_ids = self.env.user.groups_id.ids
        domain = args + [
            '|',
            ('group_id', '=', False),
            ('group_id', 'in', user_group_ids)
        ]
        return super().name_search(name, domain, operator, limit)
