from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_commodity_journal = fields.Boolean(string='Is Commodity Revaluation Journal',
                                           help='Designates this journal for commodity revaluation entries')
