# -*- coding: utf-8 -*-

from odoo import models, fields, api



class AccountMoveLine(models.Model):
    _inherit = "account.move"

    amount_total = fields.Monetary(string='Total LOC', store=True, readonly=True,
        compute='_compute_amount',
        inverse='_inverse_amount_total')


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    product_buy_price = fields.Float(string='PS Volume', readonly=True, related="product_id.standard_price", store=True)
    # ~ product_sell_price = fields.Float(string='PS Volume', readonly=True, related="product_id.lst_price", store=True)
    


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
