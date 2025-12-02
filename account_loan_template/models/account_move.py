from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        for line in self.invoice_line_ids:
            if line.account_loan_template_id:
                account_loan = self._account_loan(line)
                account_loan.compute_lines()
        return res

    def _account_loan(self, line):
        loan_vals = line._account_loan_vals()
        loan_vals['loan_amount'] = line.total_debt - line.price_subtotal
        loan_vals['rate'] = line.initial_rate
        loan_vals['partner_id'] = line.partner_id.id
        loan_vals['account_move_line'] = line.id
        if residual_rate := loan_vals.pop('residual_rate'):
            loan_vals['residual_amount'] = (residual_rate / 100) * line.total_debt
        if loan_vals.get('name'):
            loan_vals.pop('name')
        account_loan = self.env['account.loan'].create(loan_vals)
        return account_loan

    #Asset code
    def _prepare_asset_vals(self, aml):
        depreciation_base = aml.total_debt if aml.account_loan_template_id else aml.balance
        return {
            "name": aml.name,
            "code": self.name,
            "profile_id": aml.asset_profile_id.id,
            "purchase_value": depreciation_base,
            "partner_id": aml.partner_id.id,
            "date_start": self.date,
        }

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    account_loan_template_id = fields.Many2one('account.loan.template', string="Account Loan")
    total_debt = fields.Monetary(string="Total Debt")
    initial_rate = fields.Float(string="Initial Rate (%)")

    @api.constrains('account_loan_template_id', 'total_debt', 'initial_rate')
    def _check_loan_template_fields(self):
        for line in self:
            if line.account_loan_template_id:
                if not line.total_debt:
                    raise ValidationError(
                        _('Total Debt is required when a Loan Template is selected.')
                    )
                if not line.initial_rate:
                    raise ValidationError(
                        _('Initial Rate is required when a Loan Template is selected.')
                    )


    def _account_loan_vals(self):
        template = self.account_loan_template_id
        if not template:
            return {}
        technical = {
            'id', 'create_uid', 'create_date', 'write_uid', 'write_date',
            '__last_update', 'display_name'
        }
        vals = {}
        for field_name, field in template._fields.items():
            # Skip technical fields
            if field_name in technical:
                continue

            # Skip computed fields without store
            if field.compute and not field.store:
                continue

            # Skip relational fields we don't care about
            if field.type in ('one2many', 'many2many', 'binary'):
                continue

            # Get the value
            value = getattr(template, field_name, None)

            # Handle Many2one: convert to integer ID
            if field.type == 'many2one':
                vals[field_name] = value.id if value else False
            else:
                # For all other types (char, text, integer, float, boolean, selection, date, datetime)
                vals[field_name] = value

        return vals
