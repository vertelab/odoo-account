from odoo import models, fields, api


class AccountAnalytics(models.Model):
    _inherit = 'account.analytic.account'

    def _account_users_domain(self):
        group_id = self.env.ref('account.group_account_invoice')
        return [("id", 'in', group_id.users.ids)]

    reviewer_id = fields.Many2one('res.users', string="Reviewer", domain=lambda self: self._account_users_domain())


class AccountAnalyticsLine(models.Model):
    _inherit = 'account.analytic.line'

    reviewer_id = fields.Many2one(related="account_id.reviewer_id", readonly=False)
