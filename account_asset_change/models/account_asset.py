import datetime
from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from math import copysign

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero, formatLang
from odoo.tools.date_utils import end_of

class AccountAsset(models.Model):
    _inherit = 'account.asset'

    depreciation_move_ids = fields.One2many('account.move.line', 'asset_id', string='Depreciation Lines')
    original_move_line_ids = fields.Many2many(comodel_name='account.move.line', relation='asset_move_line_rel', column1='asset_id', column2='line_id', string='Journal Items', copy=False)

    
    account_asset_id = fields.Many2one(
        comodel_name='account.account',
        string='Fixed Asset Account',
        compute='_compute_account_asset_id',
        help="Account used to record the purchase of the asset at its original price.",
        store=True, readonly=False,
        check_company=True,
        domain="[('account_type', '!=', 'off_balance')]",
    )

    @api.depends('account_depreciation_id', 'account_depreciation_expense_id', 'original_move_line_ids')
    def _compute_account_asset_id(self):
        for record in self:
            if record.original_move_line_ids:
                if len(record.original_move_line_ids.account_id) > 1:
                    raise UserError(_("All the lines should be from the same account"))
                record.account_asset_id = record.original_move_line_ids.account_id
            if not record.account_asset_id:
                # Only set a default value, do not erase user inputs
                record._onchange_account_depreciation_id()

    account_depreciation_id = fields.Many2one(
        comodel_name='account.account',
        string='Depreciation Account',
        check_company=True,
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card', 'off_balance')), ('deprecated', '=', False)]",
        help="Account used in the depreciation entries, to decrease the asset value."
    )
    account_depreciation_expense_id = fields.Many2one(
        comodel_name='account.account',
        string='Expense Account',
        check_company=True,
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card', 'off_balance')), ('deprecated', '=', False)]",
        help="Account used in the periodical entries, to record a part of the asset as expense.",
    )


    @api.onchange('account_depreciation_id')
    def _onchange_account_depreciation_id(self):
        if not self.original_move_line_ids:
            if not self.account_asset_id and self.state != 'model':
                # Only set a default value since it is visible in the form
                self.account_asset_id = self.account_depreciation_id

    def _get_own_book_value(self, date=None):
        self.ensure_one()
        return (self._get_residual_value_at_date(date) if date else self.value_residual) + self.salvage_value

    def _get_residual_value_at_date(self, date):
        """ Computes the theoretical value of the asset at a specific date.

            :param date: the date at which we want the asset's value
            :return: the value at date of the asset without taking reverse entries into account (as it should be in a "normal" flow of the asset)
        """
        current_and_previous_depreciation = self.depreciation_move_ids.filtered(
            lambda mv:
            mv.asset_depreciation_beginning_date < date
            and not mv.reversed_entry_id
        ).sorted('asset_depreciation_beginning_date', reverse=True)
        if not current_and_previous_depreciation:
            return 0

        if len(current_and_previous_depreciation) > 1:
            previous_value_residual = current_and_previous_depreciation[1].asset_remaining_value
        else:
            # If there is only one depreciation, we take the original depreciation value
            previous_value_residual = self.original_value - self.salvage_value - self.already_depreciated_amount_import

        # We compare the amount_residuals of the depreciations before and during the given date.
        # It applies the ratio of the period (to-given-date / total-days-of-the-period) to the amount of the depreciation.
        cur_depr_end_date = self._get_end_period_date(date)
        current_depreciation = current_and_previous_depreciation[0]
        cur_depr_beg_date = current_depreciation.asset_depreciation_beginning_date

        rate = self._get_delta_days(cur_depr_beg_date, date) / self._get_delta_days(cur_depr_beg_date, cur_depr_end_date)
        lost_value_at_date = (previous_value_residual - current_depreciation.asset_remaining_value) * rate
        residual_value_at_date = self.currency_id.round(previous_value_residual - lost_value_at_date)
        if self.currency_id.compare_amounts(self.original_value, 0) > 0:
            return max(residual_value_at_date, 0)
        else:
            return min(residual_value_at_date, 0)



    def action_asset_change(self):
        """ Returns an action opening the asset modification wizard.
        """
        self.ensure_one()
        new_wizard = self.env['asset.change'].create({
            'asset_id': self.id,
            'modify_action': 'resume' if self.env.context.get('resume_after_pause') else 'dispose',
        })
        return {
            'name': _('Change Asset'),
            'view_mode': 'form',
            'res_model': 'asset.change',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': new_wizard.id,
            'context': self.env.context,
        }


    def move_analytic(self):
        
        pass
        
        
    def resume_after_pause(self):
        """ Sets an asset in 'paused' state back to 'open'.
        A Depreciation line is created automatically to remove  from the
        depreciation amount the proportion of time spent
        in pause in the current period.
        """
        self.ensure_one()
        return self.with_context(resume_after_pause=True).action_asset_modify()

    def pause(self, pause_date, message=None):
        """ Sets an 'open' asset in 'paused' state, generating first a depreciation
        line corresponding to the ratio of time spent within the current depreciation
        period before putting the asset in pause. This line and all the previous
        unposted ones are then posted.
        """
        self.ensure_one()
        self._create_move_before_date(pause_date)
        self.write({'state': 'paused'})
        self.message_post(body=_("Asset paused. %s", message if message else ""))


