from odoo import api, fields, models
from odoo.tools.float_utils import float_compare
from odoo.tools.sql import column_exists, create_column

_release_to_pay_status_list = [('yes', 'Yes'), ('no', 'No'), ('exception', 'Exception')]


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _auto_init(self):
        if not column_exists(self.env.cr, "account_move", "release_to_pay"):
            self.env.cr.execute("ALTER TABLE account_move ADD COLUMN release_to_pay VARCHAR DEFAULT 'exception'")
        return super()._auto_init()

    release_to_pay = fields.Selection(
        _release_to_pay_status_list,
        compute='_compute_release_to_pay',
        copy=False,
        store=True,
        help="This field can take the following values :\n"
             "  * Yes: you should pay the bill, you have received the products\n"
             "  * No, you should not pay the bill, you have not received the products\n"
             "  * Exception, there is a difference between received and billed quantities\n"
             "This status is defined automatically, but you can force it by ticking the 'Force Status' checkbox.")
    release_to_pay_manual = fields.Selection(
        _release_to_pay_status_list,
        string='Should Be Paid',
        compute='_compute_release_to_pay_manual', store='True', readonly=False,
        help="  * Yes: you should pay the bill, you have received the products\n"
             "  * No, you should not pay the bill, you have not received the products\n"
             "  * Exception, there is a difference between received and billed quantities\n"
             "This status is defined automatically, but you can force it by ticking the 'Force Status' checkbox.")
    force_release_to_pay = fields.Boolean(
        string="Force Status",
        help="Indicates whether the 'Should Be Paid' status is defined automatically or manually.")

    @api.depends('invoice_line_ids.can_be_paid', 'force_release_to_pay', 'payment_state')
    def _compute_release_to_pay(self):
        records = self
        if self.env.context.get('module') == 'account_3way_match_ce':
            records = records.filtered(lambda r: r.payment_state != 'paid' and r.move_type in ('in_invoice', 'in_refund'))
            (self - records).release_to_pay = 'no'
        for invoice in records:
            if invoice.payment_state == 'paid' or not invoice.is_invoice(include_receipts=True):
                invoice.release_to_pay = 'no'
            elif invoice.force_release_to_pay:
                invoice.release_to_pay = invoice.release_to_pay_manual
            else:
                result = None
                for invoice_line in invoice.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_subsection', 'line_note')):
                    line_status = invoice_line.can_be_paid
                    if line_status == 'exception':
                        result = 'exception'
                        break
                    elif not result:
                        result = line_status
                    elif line_status != result:
                        result = 'exception'
                        break
                invoice.release_to_pay = result or 'no'

    @api.depends('release_to_pay', 'force_release_to_pay')
    def _compute_release_to_pay_manual(self):
        for invoice in self:
            if not (invoice.payment_state == 'paid' or not invoice.is_invoice(include_receipts=True) or invoice.force_release_to_pay):
                invoice.release_to_pay_manual = invoice.release_to_pay

    @api.onchange('release_to_pay_manual')
    def _onchange_release_to_pay_manual(self):
        if self.release_to_pay and self.release_to_pay_manual != self.release_to_pay:
            self.force_release_to_pay = True


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _auto_init(self):
        if not column_exists(self.env.cr, "account_move_line", "can_be_paid"):
            self.env.cr.execute("ALTER TABLE account_move_line ADD COLUMN can_be_paid VARCHAR DEFAULT 'exception'")
        return super()._auto_init()

    @api.depends('purchase_line_id.qty_received', 'purchase_line_id.qty_invoiced', 'purchase_line_id.product_qty', 'price_unit')
    def _can_be_paid(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit')
        for invoice_line in self:
            po_line = invoice_line.purchase_line_id
            if po_line:
                invoiced_qty = po_line.qty_invoiced
                received_qty = po_line.qty_received
                ordered_qty = po_line.product_qty

                invoice_currency = invoice_line.currency_id
                order_currency = po_line.currency_id
                invoice_converted_price = invoice_currency._convert(
                    invoice_line.price_unit, order_currency, invoice_line.company_id, fields.Date.today())
                if order_currency.compare_amounts(po_line.price_unit, invoice_converted_price) != 0:
                    invoice_line.can_be_paid = 'exception'
                    continue

                if po_line.product_id.purchase_method == 'purchase':
                    invoice_line._can_be_paid_ordered_qty(invoiced_qty, received_qty, ordered_qty, precision)
                else:
                    invoice_line._can_be_paid_received_qty(invoiced_qty, received_qty, ordered_qty, precision)
            else:
                invoice_line.can_be_paid = 'exception'

    def _can_be_paid_ordered_qty(self, invoiced_qty, received_qty, ordered_qty, precision):
        if float_compare(invoiced_qty - self.quantity, ordered_qty, precision_digits=precision) >= 0:
            self.can_be_paid = 'no'
        elif float_compare(invoiced_qty, ordered_qty, precision_digits=precision) <= 0:
            self.can_be_paid = 'yes'
        else:
            self.can_be_paid = 'exception'

    def _can_be_paid_received_qty(self, invoiced_qty, received_qty, ordered_qty, precision):
        if float_compare(invoiced_qty, received_qty, precision_digits=precision) <= 0:
            self.can_be_paid = 'yes'
        elif received_qty == 0 and float_compare(invoiced_qty, ordered_qty, precision_digits=precision) <= 0:
            self.can_be_paid = 'no'
        else:
            self.can_be_paid = 'exception'

    can_be_paid = fields.Selection(
        _release_to_pay_status_list,
        compute='_can_be_paid',
        copy=False,
        store=True,
        string='Release to Pay')
