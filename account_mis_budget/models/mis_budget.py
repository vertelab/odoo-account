from odoo import fields, models, _
from odoo.exceptions import ValidationError


class MisBudget(models.Model):
    _inherit = "mis.budget"
    date_type = fields.Many2one('date.range.type', string='Date type', required=True) # Month, Weeks, Every two weeks

    def action_aggregate_budget(self):
        active_ids = self.env.context.get('active_ids')
        budget_ids = self.env['mis.budget'].browse(active_ids)

        date_from = all(self._check_same_date(budget_ids.mapped('date_from')))
        date_to = all(self._check_same_date(budget_ids.mapped('date_to')))

        if not date_from and not date_to:
            raise ValidationError("Accounts are not in the same date range")

        mis_budget_id = self.env['mis.budget'].create({
            'name': 'New Budget',
            'date_range_id': budget_ids[0].date_range_id.id,
            'date_from': budget_ids[0].date_from,
            'date_to': budget_ids[0].date_to,
            'report_id': budget_ids[0].report_id.id
        })

        if mis_budget_id:

            body = _('%s was aggregated from:', mis_budget_id.name)
            body += '<ul>'

            for budget_id in budget_ids:
                for budget_item in budget_id.item_ids:
                    item_id = self.env['mis.budget.item'].search([
                        ('date_from', '=', budget_item.date_from),
                        ('date_to', '=', budget_item.date_to),
                        ('kpi_expression_id', '=', budget_item.kpi_expression_id.id),
                        ('budget_id', '=', mis_budget_id.id)
                    ])
                    if not item_id:
                        item_id = budget_item.copy({'budget_id': mis_budget_id.id})
                    else:
                        item_id.write({
                            'amount': item_id.amount + budget_item.amount,
                        })

                body += "<li class='text-info'>%s</li>" % budget_id.name

            body += '</ul>'
            mis_budget_id.message_post(body=body)

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
