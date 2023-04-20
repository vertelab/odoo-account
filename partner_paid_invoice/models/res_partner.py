from odoo import models, fields, api, _
from ast import literal_eval


class Partner(models.Model):
    _inherit = 'res.partner'

    total_paid_invoiced = fields.Monetary(compute='_paid_invoice_total', string="Total Paid Invoiced",
                                     groups='account.group_account_invoice')

    @api.multi
    def _paid_invoice_total(self):
        account_invoice_report = self.env['account.invoice.report']
        if not self.ids:
            return True

        user_currency_id = self.env.user.company_id.currency_id.id
        all_partners_and_children = {}
        all_partner_ids = []
        for partner in self:
            # price_total is in the company currency
            all_partners_and_children[partner] = self.with_context(active_test=False).search(
                [('id', 'child_of', partner.id)]).ids
            all_partner_ids += all_partners_and_children[partner]

        # searching account.invoice.report via the ORM is comparatively expensive
        # (generates queries "id in []" forcing to build the full table).
        # In simple cases where all invoices are in the same currency than the user's company
        # access directly these elements

        # generate where clause to include multicompany rules
        where_query = account_invoice_report._where_calc([
            ('partner_id', 'in', all_partner_ids), ('state', '=', 'paid'),
            ('type', 'in', ('out_invoice', 'out_refund'))
        ])
        account_invoice_report._apply_ir_rules(where_query, 'read')
        from_clause, where_clause, where_clause_params = where_query.get_sql()

        # price_total is in the company currency
        query = """
                      SELECT SUM(price_total) as total, partner_id
                        FROM account_invoice_report account_invoice_report
                       WHERE %s
                       GROUP BY partner_id
                    """ % where_clause
        self.env.cr.execute(query, where_clause_params)
        price_totals = self.env.cr.dictfetchall()
        for partner, child_ids in all_partners_and_children.items():
            partner.total_paid_invoiced = sum(price['total'] for price in price_totals if price['partner_id'] in child_ids)

    @api.multi
    def action_view_partner_invoices_paid(self):
        self.ensure_one()
        action = self.env.ref('account.action_invoice_refund_out_tree').read()[0]
        action['domain'] = literal_eval(action['domain'])
        action['domain'].append(('partner_id', 'child_of', self.id))
        action['domain'].append(('state', '=', 'paid'))
        return action

