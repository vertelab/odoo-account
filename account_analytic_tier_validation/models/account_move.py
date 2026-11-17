from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends("invoice_line_ids", "invoice_line_ids.analytic_distribution")
    def _compute_analytic_reviewer_ids(self):
        for record in self:
            if record.invoice_line_ids:
                record.analytic_reviewer_ids = self._distribution_account_users(
                    record.invoice_line_ids.mapped('analytic_distribution')
                )
            else:
                record.analytic_reviewer_ids = False

    analytic_reviewer_ids = fields.Many2many(
        'res.users',
        'account_move_analytic_reviewer_rel',
        'move_id', 'user_id',
        string="Cost Center Reviewers",
        compute='_compute_analytic_reviewer_ids',
        store=True,
    )

    def _distribution_account_users(self, analytic_distributions):
        """Collect the reviewers of the analytic accounts in a distribution.

        Odoo 18 stores the distribution as a JSON dict of
        ``{"<account id>": <percent>}`` per line; ``mapped`` on a list of
        dicts gives the dicts, so the keys are collected explicitly.
        """
        user_ids = self.env['res.users']
        for distribution_line in analytic_distributions:
            if not distribution_line:
                continue
            account_ids = [int(key) for key in distribution_line.keys()]
            analytic_accounts = self.env['account.analytic.account'].browse(account_ids)
            user_ids |= analytic_accounts.mapped('reviewer_id')
        return user_ids
