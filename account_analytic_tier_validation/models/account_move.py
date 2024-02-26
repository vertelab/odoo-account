from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends("line_ids", "invoice_line_ids")
    def get_reviewers_from_line(self):
        for record in self:
            if record.invoice_line_ids:
                reviewer_ids = self._distribution_account_users(record.invoice_line_ids.mapped('analytic_distribution'))
                record.analytic_reviewer_ids = reviewer_ids.ids
            else:
                record.analytic_reviewer_ids = False

    analytic_reviewer_ids = fields.Many2many('res.users', string="Cost Center Reviewers", compute=get_reviewers_from_line, store=True)

    def _distribution_account_users(self, analytic_distributions: list):
        # [{'8': 100.0, '15': 20.0}, {'7': 100.0}]
        user_ids = self.env['res.users']
        for distribution_line in analytic_distributions:
            if distribution_line:
                account_ids = list(map(lambda account_id: int(account_id), distribution_line.keys()))
                analytic_account_ids = self.env['account.analytic.account'].browse(account_ids)
                print(analytic_account_ids)
                user_ids += analytic_account_ids.mapped('reviewer_id')
        return user_ids


