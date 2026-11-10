from odoo import models, api, fields


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    @api.depends('plan_id', 'name')
    def _compute_display_name(self):
        for _rec in self:
            _rec.display_name = '%s %s ' % (
                '%s /' % _rec.plan_id.name if _rec.plan_id else '',
                _rec.name)

    display_name = fields.Char(string="Display Name", compute=_compute_display_name)
