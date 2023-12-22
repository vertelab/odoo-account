from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    interval_number = fields.Integer(string="Interval Number", config_parameter='enablebanking.interval_number')

    interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')], string="Interval Type", config_parameter='enablebanking.interval_type')


    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env.ref('account_enablebanking.enable_banking_transaction_sync').write({
            'interval_number': self.interval_number,
            'interval_type': self.interval_type
        })