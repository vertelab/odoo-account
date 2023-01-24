# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMoveline(models.Model):
    _inherit = 'account.move.line'

    total_weight = fields.Float(string='Total Weight', readonly=True, compute='_compute_total_weight')

    product_buy_price = fields.Float(string='PS Volume', readonly=True, related="product_id.standard_price", store=True)

    def _compute_total_weight(self):
        context_copy = self.env.context.copy()
        context_copy.update({'check_move_period_validity':False})
        for record in self:
            quantity = record.quantity if record.quantity else 0
            if record.product_id:
                weight = record.product_id.weight if record.product_id.weight else 0
            else:
                weight = 0
            record.with_context(context_copy).write({'total_weight':weight * quantity})


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ~ @api.depends(
        # ~ 'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        # ~ 'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        # ~ 'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        # ~ 'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        # ~ 'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        # ~ 'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        # ~ 'line_ids.debit',
        # ~ 'line_ids.credit',
        # ~ 'line_ids.currency_id',
        # ~ 'line_ids.amount_currency',
        # ~ 'line_ids.amount_residual',
        # ~ 'line_ids.amount_residual_currency',
        # ~ 'line_ids.payment_id.state',
        # ~ 'line_ids.full_reconcile_id')
    # ~ def _compute_amount(self):
        # ~ res = super(AccountMove, self)._compute_amount()
        # ~ context_copy = self.env.context.copy()
        # ~ context_copy.update({'check_move_period_validity':False})
        # ~ for move in self:
             # ~ move.with_context(context_copy).write({'amount_total_loc':move.amount_total})
        # ~ return res

    @api.depends('amount_total','amount_total_signed')
    def _compute_amount_loc(self):
        context_copy = self.env.context.copy()
        context_copy.update({'check_move_period_validity':False})
        for move in self:
            if ((move.amount_total_signed >= 0 and move.amount_total >= 0) or
                    (move.amount_total_signed < 0 and move.amount_total < 0)):
                move.with_context(context_copy).write({'amount_total_loc': move.amount_total})
            else:
                move.with_context(context_copy).write({'amount_total_loc': -move.amount_total})

    amount_total_loc = fields.Monetary(string='Total LOC', store=True, readonly=True,
                                       compute='_compute_amount_loc')


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    product_buy_price = fields.Float(string='PS Volume', readonly=True)
    # ~ product_sell_price = fields.Float(string='PS Volume', readonly=True, related="product_id.lst_price", store=True)

    @api.model
    def _select(self):
        return '''
            SELECT
                line.id,
                line.move_id,
                line.product_id,
                line.product_buy_price * line.quantity AS product_buy_price,
                line.account_id,
                line.analytic_account_id,
                line.journal_id,
                line.company_id,
                line.company_currency_id,
                line.partner_id AS commercial_partner_id,
                move.state,
                move.move_type,
                move.partner_id,
                move.invoice_user_id,
                move.fiscal_position_id,
                move.payment_state,
                move.invoice_date,
                move.invoice_date_due,
                uom_template.id                                             AS product_uom_id,
                template.categ_id                                           AS product_categ_id,
                line.quantity / NULLIF(COALESCE(uom_line.factor, 1) / COALESCE(uom_template.factor, 1), 0.0) * (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
                                                                            AS quantity,
                -line.balance * currency_table.rate                         AS price_subtotal,
                -COALESCE(
                   -- Average line price
                   (line.balance / NULLIF(line.quantity, 0.0)) * (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
                   -- convert to template uom
                   * (NULLIF(COALESCE(uom_line.factor, 1), 0.0) / NULLIF(COALESCE(uom_template.factor, 1), 0.0)),
                   0.0) * currency_table.rate                               AS price_average,
                COALESCE(partner.country_id, commercial_partner.country_id) AS country_id
        '''

