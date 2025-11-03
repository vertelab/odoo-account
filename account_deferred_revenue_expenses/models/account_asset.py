from odoo import models, fields, api, _

class AccountAsset(models.Model):
    _inherit = 'account.asset'

    rec_type = fields.Selection([
        ('asset', 'Asset'),
        ('deferred_expense', 'Accrued Expense'),
        ('deferred_income', 'Accrued Income')], default='asset', string="Type")

    def name_get(self):
        l = []
        for rec in self:
            l.append((rec.id,rec.name))
        return l

class AccountAssetProfile(models.Model):
    _inherit = 'account.asset.profile'

    rec_type = fields.Selection([
        ('asset', 'Asset'),
        ('deferred_expense', 'Accrued Expense'),
        ('deferred_income', 'Accrued Income')], default='asset', string="Type")
