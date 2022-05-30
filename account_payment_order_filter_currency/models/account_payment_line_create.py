from locale import currency
from odoo import _, api, fields, models

class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def account_payment_line_create_action(self):
        action = {
            "name": _("Create Transactions from Move Lines"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment.line.create",
            "view_mode": "form",
            "target": "new",
            "context": self._context,
        }
        return action




class AccountPaymentLineCreate(models.TransientModel):
    _inherit  = "account.payment.line.create"

    def _get_default_currency(self):
        ''' Get the default currency from either the journal, either the default journal's company. '''
        # ~ params = self._context.get('params')
        # ~ order_id = self.env[params.get('model')].browse(params.get('id'))
        order_id = self.env['account.payment.order'].browse(self.env.context.get('active_id', False))
        
        return order_id.journal_id.currency_id or order_id.journal_id.company_id.currency_id 


    currency_id = fields.Many2one('res.currency', string='Currency', default=_get_default_currency)

    def _prepare_move_line_domain(self):
        self.ensure_one()
        domain = [
            ("reconciled", "=", False),
            ("company_id", "=", self.order_id.company_id.id),
        ]
        if self.journal_ids:
            domain += [("journal_id", "in", self.journal_ids.ids)]
        if self.partner_ids:
            domain += [("partner_id", "in", self.partner_ids.ids)]
        if self.target_move == "posted":
            domain += [("move_id.state", "=", "posted")]
        if not self.allow_blocked:
            domain += [("blocked", "!=", True)]
        if self.currency_id:
            domain += [("currency_id", "=", self.currency_id.id)]
        if self.date_type == "due":
            domain += [
                "|",
                ("date_maturity", "<=", self.due_date),
                ("date_maturity", "=", False),
            ]
        elif self.date_type == "move":
            domain.append(("date", "<=", self.move_date))
        if self.invoice:
            domain.append(
                (
                    "move_id.move_type",
                    "in",
                    ("in_invoice", "out_invoice", "in_refund", "out_refund"),
                )
            )
        if self.payment_mode:
            if self.payment_mode == "same":
                domain.append(
                    ("payment_mode_id", "=", self.order_id.payment_mode_id.id)
                )
            elif self.payment_mode == "same_or_null":
                domain += [
                    "|",
                    ("payment_mode_id", "=", False),
                    ("payment_mode_id", "=", self.order_id.payment_mode_id.id),
                ]

        if self.order_id.payment_type == "outbound":
            # For payables, propose all unreconciled credit lines,
            # including partially reconciled ones.
            # If they are partially reconciled with a supplier refund,
            # the residual will be added to the payment order.
            #
            # For receivables, propose all unreconciled credit lines.
            # (ie customer refunds): they can be refunded with a payment.
            # Do not propose partially reconciled credit lines,
            # as they are deducted from a customer invoice, and
            # will not be refunded with a payment.
            domain += [
                ("credit", ">", 0),
                ("account_id.internal_type", "in", ["payable", "receivable"]),
            ]
        elif self.order_id.payment_type == "inbound":
            domain += [
                ("debit", ">", 0),
                ("account_id.internal_type", "in", ["receivable", "payable"]),
            ]
        # Exclude lines that are already in a non-cancelled
        # and non-uploaded payment order; lines that are in a
        # uploaded payment order are proposed if they are not reconciled,
        paylines = self.env["account.payment.line"].search(
            [
                ("state", "in", ("draft", "open", "generated")),
                ("move_line_id", "!=", False),
            ]
        )
        if paylines:
            move_lines_ids = [payline.move_line_id.id for payline in paylines]
            domain += [("id", "not in", move_lines_ids)]
        domain += [("move_id.exclude_payment", "=", False)]
        return domain



    
class AccountMove(models.Model):
    _inherit = 'account.move'

    exclude_payment = fields.Boolean(string="Exclude Payment")


class AccountPaymentLine(models.Model):
    _inherit = "account.payment.line"

    invoice_date = fields.Date(related="move_line_id.move_id.invoice_date", readonly=True, string="Invoice Date", store=True)
    ml_maturity_date = fields.Date(related="move_line_id.date_maturity", readonly=True, store=True)