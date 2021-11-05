from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def setting_init_fiscal_year_action(self):
        """ Called by the 'Fiscal Year Opening' button of the setup bar."""
        #company = self.env.company
        #company.create_op_move_if_non_existant()
        # new_wizard = self.env['account.fiscalyear'].create({'company_id': company.id})
        view_id = self.env.ref('account_period.view_account_fiscalyear_form').id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Accounting Periods'),
            'view_mode': 'form',
            'res_model': 'account.fiscalyear',
            'target': 'new',
            # 'res_id': new_wizard.id,
            'views': [[view_id, 'form']],
        }
