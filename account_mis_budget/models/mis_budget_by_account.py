from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class MisBudgetByAccount(models.Model):
    _inherit = "mis.budget.by.account"

    def action_aggregate_account_budget(self):
        active_ids = self.env.context.get('active_ids')
        account_budget_ids = self.env['mis.budget.by.account'].browse(active_ids)

        date_from = all(self._check_same_date(account_budget_ids.mapped('date_from')))
        date_to = all(self._check_same_date(account_budget_ids.mapped('date_to')))

        if not date_from and not date_to:
            raise ValidationError("Accounts are not in the same date range")

        budget_id = self.env['mis.budget.by.account'].create({
            'name': 'New Budget',
            'date_range_id': account_budget_ids[0].date_range_id.id,
            'date_from': account_budget_ids[0].date_from,
            'date_to': account_budget_ids[0].date_to,
        })

        if budget_id:

            body = _('%s was aggregated from:', budget_id.name)
            body += '<ul>'

            for account_budget_id in account_budget_ids:
                for account_item in account_budget_id.item_ids:
                    item_id = self.env['mis.budget.by.account.item'].search([
                        ('date_from', '=', account_item.date_from),
                        ('date_to', '=', account_item.date_to),
                        ('account_id', '=', account_item.account_id.id),
                        ('budget_id', '=', budget_id.id)
                    ])
                    if not item_id:
                        item_id = account_item.copy({'budget_id': budget_id.id})
                    else:
                        item_id.write({
                            'balance': item_id.balance + account_item.balance,
                        })

                body += "<li class='text-info'>%s</li>" % account_budget_id.name

            body += '</ul>'
            budget_id.message_post(body=body)

    def _check_same_date(self, date_time_list):
        valid = []
        for count in range(len(date_time_list)):
            for date_time in date_time_list:
                if date_time == date_time_list[count]:
                    valid.append(True)
                else:
                    valid.append(False)
            break
        return valid

