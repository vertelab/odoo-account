"""Release-to-pay för leverantörsfakturor (3-vägsmatchning).

Modulen märker varje leverantörsfaktura med ett tillstånd som svarar på om
den får betalas: `yes`, `no` eller `exception`. Tillståndet beräknas per rad
utifrån beställd, mottagen och fakturerad kvantitet samt prisjämförelse mot
inköpsordern, och sammanställs sedan till fakturans tillstånd.

Fälten är avsiktligt namngivna som i Enterprise-modulen `account_3way_match`
så att befintliga installationer kan migreras utan att kolumner byter namn.
"""

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare
from odoo.tools.sql import column_exists

# Tillstånden en faktura eller fakturarad kan ha.
RELEASE_TO_PAY_STATES = [
    ('yes', 'Yes'),
    ('no', 'No'),
    ('exception', 'Exception'),
]

# Modulnamnet används för att känna igen installationskörningen, då
# irrelevanta fakturor kan sättas till 'no' i ett svep i stället för att
# beräknas en och en.
_MODULE = 'account_3way_match_ce'


def _is_bill(move):
    """En verifikation som 3-vägsmatchningen gäller (leverantörsfaktura)."""
    return move.move_type in ('in_invoice', 'in_refund')


def _billable_lines(move):
    """Fakturans rader som bär kvantitet och pris (inte sektioner/noter)."""
    return move.invoice_line_ids.filtered(
        lambda line: line.display_type not in ('line_section', 'line_subsection', 'line_note'))


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _auto_init(self):
        # Kolumnen skapas med default 'exception' på databasnivå innan fältet
        # beräknas. Det undviker en tung omräkning av alla befintliga rader
        # vid installation, och är idempotent (guarden hindrar en andra ALTER).
        if not column_exists(self.env.cr, 'account_move', 'release_to_pay'):
            self.env.cr.execute(
                "ALTER TABLE account_move ADD COLUMN release_to_pay VARCHAR DEFAULT 'exception'")
        return super()._auto_init()

    release_to_pay = fields.Selection(
        RELEASE_TO_PAY_STATES,
        compute='_compute_release_to_pay',
        copy=False,
        store=True,
        help="Om fakturan får betalas:\n"
             "  * Yes: varorna är mottagna, fakturan kan betalas\n"
             "  * No: varorna är inte mottagna, betala inte\n"
             "  * Exception: skillnad mellan mottagen och fakturerad kvantitet\n"
             "Tillståndet beräknas automatiskt men kan tvingas manuellt "
             "genom att sätta 'Force Status'.")
    release_to_pay_manual = fields.Selection(
        RELEASE_TO_PAY_STATES,
        string='Should Be Paid',
        compute='_compute_release_to_pay_manual',
        store=True,
        readonly=False,
        help="Manuellt satt betalstatus. Används när 'Force Status' är satt.")
    force_release_to_pay = fields.Boolean(
        string="Force Status",
        help="Om satt styrs tillståndet av det manuella värdet i stället "
             "för av den automatiska beräkningen.")

    @api.depends('invoice_line_ids.can_be_paid', 'force_release_to_pay', 'payment_state')
    def _compute_release_to_pay(self):
        # Under installationen är endast fakturor som kan behöva betalas
        # relevanta; övriga sätts till 'no' i ett svep.
        if self.env.context.get('module') == _MODULE:
            relevant = self.filtered(
                lambda move: move.payment_state != 'paid' and _is_bill(move))
            (self - relevant).release_to_pay = 'no'
        else:
            relevant = self

        for move in relevant:
            move.release_to_pay = move._release_to_pay_state()

    def _release_to_pay_state(self):
        """Fakturans tillstånd utifrån dess rader och manuella överstyrning."""
        self.ensure_one()
        if self.payment_state == 'paid' or not self.is_invoice(include_receipts=True):
            # Redan betald, eller inte en faktura — inget att betala.
            return 'no'
        if self.force_release_to_pay:
            return self.release_to_pay_manual

        lines = _billable_lines(self)
        if not lines:
            # Tom faktura — inget att betala.
            return 'no'

        states = set(lines.mapped('can_be_paid'))
        if len(states) == 1:
            # Alla rader delar tillstånd — fakturan får det tillståndet.
            return states.pop()
        # Rader med olika tillstånd (inkl. någon i 'exception') gör fakturan
        # till en exception.
        return 'exception'

    @api.depends('release_to_pay', 'force_release_to_pay')
    def _compute_release_to_pay_manual(self):
        for move in self:
            if move.force_release_to_pay:
                continue
            if move.payment_state == 'paid' or not move.is_invoice(include_receipts=True):
                continue
            move.release_to_pay_manual = move.release_to_pay

    @api.onchange('release_to_pay_manual')
    def _onchange_release_to_pay_manual(self):
        # Att ange ett manuellt värde som skiljer sig från det beräknade
        # aktiverar överstyrningen.
        if self.release_to_pay and self.release_to_pay_manual != self.release_to_pay:
            self.force_release_to_pay = True


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _auto_init(self):
        if not column_exists(self.env.cr, 'account_move_line', 'can_be_paid'):
            self.env.cr.execute(
                "ALTER TABLE account_move_line ADD COLUMN can_be_paid VARCHAR DEFAULT 'exception'")
        return super()._auto_init()

    can_be_paid = fields.Selection(
        RELEASE_TO_PAY_STATES,
        compute='_can_be_paid',
        copy=False,
        store=True,
        string='Release to Pay')

    @api.depends('purchase_line_id.qty_received', 'purchase_line_id.qty_invoiced',
                 'purchase_line_id.product_qty', 'price_unit')
    def _can_be_paid(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit')
        for line in self:
            order_line = line.purchase_line_id
            if not order_line:
                # Rad utan koppling till inköpsorder kan inte matchas.
                line.can_be_paid = 'exception'
                continue
            if line._price_differs_from_order(order_line):
                line.can_be_paid = 'exception'
                continue
            line.can_be_paid = line._quantity_state(order_line, precision)

    def _price_differs_from_order(self, order_line):
        """True om fakturaradens pris skiljer sig från inköpsorderns pris."""
        self.ensure_one()
        converted = self.currency_id._convert(
            self.price_unit, order_line.currency_id, self.company_id, fields.Date.today())
        return order_line.currency_id.compare_amounts(order_line.price_unit, converted) != 0

    def _quantity_state(self, order_line, precision):
        """Tillstånd utifrån produktens faktureringspolicy och kvantiteter."""
        self.ensure_one()
        invoiced = order_line.qty_invoiced
        received = order_line.qty_received
        ordered = order_line.product_qty
        if order_line.product_id.purchase_method == 'purchase':
            return self._state_on_ordered_qty(invoiced, ordered, precision)
        return self._state_on_received_qty(invoiced, received, ordered, precision)

    def _state_on_ordered_qty(self, invoiced, ordered, precision):
        """Policy 'på beställd kvantitet'."""
        self.ensure_one()
        if float_compare(invoiced - self.quantity, ordered, precision_digits=precision) >= 0:
            # Hela den beställda kvantiteten är redan fakturerad.
            return 'no'
        if float_compare(invoiced, ordered, precision_digits=precision) <= 0:
            # Faktureringen ryms inom det beställda.
            return 'yes'
        # Faktureringen överstiger det beställda.
        return 'exception'

    def _state_on_received_qty(self, invoiced, received, ordered, precision):
        """Policy 'på mottagen kvantitet'."""
        self.ensure_one()
        if float_compare(invoiced, received, precision_digits=precision) <= 0:
            # Det fakturerade är mottaget.
            return 'yes'
        if received == 0 and float_compare(invoiced, ordered, precision_digits=precision) <= 0:
            # Inget mottaget, men inom beställd kvantitet.
            return 'no'
        # Överstiger mottaget, eller överstiger det beställda.
        return 'exception'
