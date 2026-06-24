from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class CommodityRevaluationWizard(models.TransientModel):
    _name = 'commodity.revaluation.wizard'
    _description = 'Commodity Revaluation Wizard'

    commodity_id = fields.Many2one('product.commodity', string='Commodity', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                  default=lambda self: self.env.company)
    date = fields.Date(string='Revaluation Date', required=True, default=fields.Date.today)

    old_price = fields.Monetary(string='Old Price', currency_field='currency_id',
                                 related='commodity_id.latest_price')
    currency_id = fields.Many2one('res.currency', related='commodity_id.currency_id')

    new_price = fields.Monetary(string='New Price', currency_field='currency_id')
    price_difference = fields.Monetary(string='Price Difference', currency_field='currency_id',
                                        compute='_compute_difference')
    inventory_value_current = fields.Monetary(string='Current Inventory Value',
                                               currency_field='currency_id',
                                               compute='_compute_inventory')
    inventory_value_new = fields.Monetary(string='New Inventory Value',
                                           currency_field='currency_id',
                                           compute='_compute_inventory')
    difference_value = fields.Monetary(string='Value Difference',
                                        currency_field='currency_id',
                                        compute='_compute_inventory')
    line_ids = fields.One2many('commodity.revaluation.line', 'wizard_id',
                                 string='Inventory Lines', compute='_compute_inventory_lines')

    journal_id = fields.Many2one('account.journal', string='Journal',
                                  domain=[('is_commodity_journal', '=', True)])
    gain_account_id = fields.Many2one('account.account', string='Gain Account')
    loss_account_id = fields.Many2one('account.account', string='Loss Account')
    reason = fields.Text(string='Reason', default='Commodity price revaluation')

    @api.depends('old_price', 'new_price')
    def _compute_difference(self):
        for w in self:
            w.price_difference = (w.new_price or 0.0) - (w.old_price or 0.0)

    def _compute_inventory(self):
        for w in self:
            products = self.env['product.product'].search([
                ('commodity_id', '=', w.commodity_id.id),
            ])
            total_value = sum(p.qty_available * p.standard_price for p in products)
            total_qty = sum(p.qty_available for p in products)
            w.inventory_value_current = total_value
            if w.new_price and w.old_price and w.commodity_id.grams_per_unit:
                per_gram_diff = (w.new_price - w.old_price) / w.commodity_id.grams_per_unit
                w.inventory_value_new = total_value
                w.difference_value = total_qty * per_gram_diff
            else:
                w.inventory_value_new = total_value
                w.difference_value = 0.0

    @api.depends('commodity_id')
    def _compute_inventory_lines(self):
        for w in self:
            lines = []
            products = self.env['product.product'].search([
                ('commodity_id', '=', w.commodity_id.id),
                ('is_commodity_raw_material', '=', True),
            ])
            for p in products:
                qty = p.qty_available
                if qty > 0:
                    old_val = qty * p.standard_price
                    lines.append((0, 0, {
                        'product_id': p.id,
                        'product_qty': qty,
                        'old_unit_price': p.standard_price,
                        'old_value': old_val,
                        'new_unit_price': w.new_price or 0.0,
                        'new_value': qty * (w.new_price or 0.0),
                    }))
            w.line_ids = lines

    @api.onchange('commodity_id')
    def _onchange_commodity_id(self):
        if self.commodity_id:
            self.journal_id = self.commodity_id.journal_id
            self.gain_account_id = self.commodity_id.gain_account_id
            self.loss_account_id = self.commodity_id.loss_account_id
            self.new_price = self.commodity_id.latest_price

    def action_validate(self):
        self.ensure_one()
        if not self.journal_id:
            raise UserError(_('Please select a revaluation journal.'))
        if not self.gain_account_id or not self.loss_account_id:
            raise UserError(_('Please configure Gain and Loss accounts.'))
        if not self.new_price:
            raise UserError(_('Please enter a new price.'))

        diff = self.difference_value
        if not diff:
            raise UserError(_('No price difference to revaluate.'))

        products = self.env['product.product'].search([
            ('commodity_id', '=', self.commodity_id.id),
            ('is_commodity_raw_material', '=', True),
        ])
        product_ids_with_stock = [p for p in products if p.qty_available > 0]
        if not product_ids_with_stock:
            raise UserError(_('No products with stock to revaluate.'))

        account_move_obj = self.env['account.move']
        svl_obj = self.env['stock.valuation.layer']

        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': f'Commodity Revaluation: {self.commodity_id.code}',
            'line_ids': [],
        }

        total_debit = 0.0
        total_credit = 0.0
        valuation_account = self.commodity_id.valuation_account_id

        for product in product_ids_with_stock:
            qty = product.qty_available
            quality = product.commodity_quality_id
            coefficient = quality.price_coefficient if quality else 1.0
            grams_per_unit = self.commodity_id.grams_per_unit or 1.0

            old_base_price = self.old_price or 0.0
            new_base_price = self.new_price
            old_quality_price_per_gram = (old_base_price / grams_per_unit) * coefficient
            new_quality_price_per_gram = (new_base_price / grams_per_unit) * coefficient

            value_diff = qty * (new_quality_price_per_gram - old_quality_price_per_gram)
            if abs(value_diff) < 0.01:
                continue

            if value_diff > 0:
                account_id = self.gain_account_id.id
            else:
                account_id = self.loss_account_id.id

            svl_obj.create({
                'product_id': product.id,
                'quantity': 0.0,
                'value': value_diff,
                'unit_cost': 0.0,
                'remaining_qty': 0.0,
                'remaining_value': 0.0,
                'company_id': self.company_id.id,
                'description': f'Commodity revaluation: {self.commodity_id.code} '
                               f'({self.old_price} -> {self.new_price})',
            })

            if valuation_account:
                move_vals['line_ids'] += [
                    (0, 0, {
                        'account_id': valuation_account.id,
                        'debit': value_diff if value_diff > 0 else 0.0,
                        'credit': -value_diff if value_diff < 0 else 0.0,
                        'name': f'{product.display_name}: {self.commodity_id.code} revaluation',
                        'product_id': product.id,
                    }),
                    (0, 0, {
                        'account_id': account_id,
                        'debit': -value_diff if value_diff < 0 else 0.0,
                        'credit': value_diff if value_diff > 0 else 0.0,
                        'name': f'{product.display_name}: {self.commodity_id.code} revaluation',
                        'product_id': product.id,
                    }),
                ]

        if move_vals['line_ids']:
            move = account_move_obj.create(move_vals)
            move.action_post()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'commodity.revaluation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
            'res_id': self.id,
        }


class CommodityRevaluationLine(models.TransientModel):
    _name = 'commodity.revaluation.line'
    _description = 'Commodity Revaluation Line'

    wizard_id = fields.Many2one('commodity.revaluation.wizard', string='Wizard', required=True,
                                 ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_qty = fields.Float(string='Quantity')
    currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id')
    old_unit_price = fields.Float(string='Old Unit Price', digits=(16, 4))
    old_value = fields.Float(string='Old Value', digits=(16, 4))
    new_unit_price = fields.Float(string='New Unit Price', digits=(16, 4))
    new_value = fields.Float(string='New Value', digits=(16, 4))
    difference = fields.Float(string='Difference', digits=(16, 4), compute='_compute_difference')

    @api.depends('old_value', 'new_value')
    def _compute_difference(self):
        for l in self:
            l.difference = l.new_value - l.old_value
