# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import re
import time
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

BASE_URL = 'https://api.fortnox.se'


def split_into_chunks(text, max_length=255):
    """Split text into chunks of maximum length, respecting sentence boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_length:
            current_chunk += (sentence + " ")
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())

            if len(sentence) > max_length:
                chunks.extend([sentence[i:i + max_length] for i in range(0, len(sentence), max_length)])
                current_chunk = ""
            else:
                current_chunk = sentence + " "

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


class CustomFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    fortnox_vat_type = fields.Selection([
        ('SEVAT', 'Swedish VAT (SEVAT)'),
        ('SEREVERSEDVAT', 'Swedish Reversed VAT (SEREVERSEDVAT)'),
        ('EUREVERSEDVAT', 'EU Reversed VAT (EUREVERSEDVAT)'),
        ('EUVAT', 'EU VAT (EUVAT)'),
        ('EXPORT', 'Export (EXPORT)')
    ], string='Fortnox VAT Type')


class AccountJournal(models.Model):
    _inherit = "account.journal"

    is_fortnox_journal = fields.Boolean(string="Is Fortnox Journal", copy=False)


class AccountInvoice(models.Model):
    _inherit = "account.move"

    fortnox_response = fields.Char(string="Fortnox Response", readonly=True, copy=False)
    fortnox_ref = fields.Char(string="Fortnox Ref", readonly=True, copy=False, store=True, compute="set_old_name")
    fortnox_status = fields.Char(string="Fortnox Status", readonly=True, copy=False)
    is_sent_to_fortnox = fields.Boolean(string="Sent To Fortnox", readonly=True, copy=False)
    tax_included_in_price = fields.Selection([
        ('tax_included_price', 'Tax Included Price'),
        ('tax_excluded_from_price', 'Tax Excluded from Price'),
        ('mixed', 'Mixed')
    ], string='Tax Inclusion in price', compute='_compute_tax_included_in_price', store=False)

    def _compute_tax_included_in_price(self):
        for move in self:
            tax_included = set()
            for line in move.line_ids:
                for tax in line.tax_ids:
                    tax_included.add(tax.price_include)

            move.tax_included_in_price = False # this is probably redundant

            tax_included = list(tax_included)

            if len(tax_included) == 0:
                move.tax_included_in_price = "tax_excluded_from_price"
            elif len(tax_included) == 1:
                move.tax_included_in_price = "tax_included_price" if tax_included[0] else "tax_excluded_from_price"
            else:
                move.tax_included_in_price = "mixed"

    def set_old_name(self):
        for record in self:
            if record.is_sent_to_fortnox and not record.fortnox_ref:
                record.fortnox_ref = record.name
            else:
                record.fortnox_ref = False

    def remove_zero_cost_lines(self):
        """Remove invoice lines with zero cost (SFM requirement)."""
        self.state = 'draft'
        for line in self.invoice_line_ids:
            if line.price_unit == 0 and line.quantity == 0:
                line.unlink()
        self.state = 'posted'

    def remove_package_products(self):
        """
        Remove package products from invoice (SFM requirement).
        Deprecated: use remove_zero_cost_lines() instead.
        """
        self.state = 'draft'
        for line in self.invoice_line_ids:
            if len(line.product_id.membership_product_ids) > 0 and line.price_unit == 0 and line.quantity == 0:
                line.unlink()
        self.state = 'posted'

    def update_invoice_status_fortnox_paid(self, fortnox_values):
        final_pay_date_string = fortnox_values.get('FinalPayDate') or fortnox_values.get('OutboundDate')
        final_pay_date = datetime.strptime(final_pay_date_string, '%Y-%m-%d').date()

        fortnox_journal = self.env['account.journal'].search([
            ('company_id', '=', self.company_id.id),
            ('is_fortnox_journal', '=', True),
            ('type', '=', 'bank')
        ])

        if not fortnox_journal:
            raise UserError(
                "No valid Journal found. Create a journal of type bank with 'Is Fortnox Journal' set to true."
            )
        elif len(fortnox_journal) > 1:
            raise UserError(
                "More than one valid journal found for Fortnox. "
                "Make sure there is only one journal of type Bank with 'Is Fortnox Journal' set to true."
            )

        for rec in self:
            payment_register_params = {
                'amount': rec.amount_residual,
                'communication': rec.payment_reference,
                'currency_id': rec.currency_id.id,
                'journal_id': fortnox_journal.id,
                'payment_date': final_pay_date if final_pay_date else rec.date,
                'payment_type': 'inbound' if rec.amount_residual > 0 else 'outbound',
                'partner_id': rec.partner_id.id,
                'partner_bank_id': fortnox_journal.bank_account_id.id,
            }

            payment_id = self.env['account.payment.register'].with_context(
                active_model='account.move',
                active_ids=rec.id,
            ).create(payment_register_params)
            payment_id.action_create_payments()

    def _reverse_invoice(self, invoice_id, credit_invoice_ref, company_id):
        """Refund the invoice (kept as-is, working fine)."""
        wiz_context = {
            'active_model': 'account.move',
            'active_ids': [invoice_id.id],
            'default_journal_id': invoice_id.journal_id
        }
        refund_invoice_wiz = self.env['account.move.reversal'].with_context(wiz_context).create({
            'journal_id': invoice_id.journal_id.id,
            'date': fields.Date.today(),
        })
        refund_invoice = self.env['account.move'].browse(refund_invoice_wiz.refund_moves()['res_id'])
        refund_invoice.action_post()
        refund_invoice.ref = credit_invoice_ref
        refund_invoice.fortnox_response = company_id.fortnox_request(
            "GET", f"{BASE_URL}/3/invoices/{credit_invoice_ref}"
        )

    def update_invoice_status_fortnox_cron(self):
        """Cron job to update invoice status from Fortnox (kept as-is, working fine)."""
        from_date = datetime.now() - timedelta(days=365)
        for company_id in self.env['res.company'].search([]):
            move_id = self.env['account.move'].search([
                ('company_id', '=', company_id.id),
                ('create_date', '>', from_date),
                ('payment_state', 'not in', ['paid', 'reversed', 'partially_paid', 'in_payment']),
                ('state', '=', 'posted'),
                ('move_type', '=', 'out_invoice')
            ])
            for invoice in move_id:
                fortnox_res = company_id.fortnox_request(
                    "GET",
                    f"{BASE_URL}/3/invoices/{invoice.fortnox_ref}"
                )

                if fortnox_res.get('ErrorInformation', {}).get('Code'):
                    pass
                elif invoice_info := fortnox_res.get('Invoice'):
                    credit_invoice_ref = int(invoice_info.get('CreditInvoiceReference'))
                    if credit_invoice_ref > 0:
                        invoice._reverse_invoice(
                            invoice_id=invoice, credit_invoice_ref=credit_invoice_ref, company_id=company_id
                        )
                    elif credit_invoice_ref == 0 and invoice_info.get("FinalPayDate") and invoice.state == 'posted':
                        invoice.update_invoice_status_fortnox_paid(invoice_info)

                invoice.fortnox_response = fortnox_res

    def sync_fortnox(self):
        """Synchronize invoice with Fortnox."""
        self.ensure_one()

        # Ensure we're working in the correct company context
        self = self.with_company(self.company_id)

        if not self.fortnox_ref and not self.is_sent_to_fortnox:
            self._fortnox_create()
            return

        fortnox_res = self.company_id.fortnox_request(
            "GET",
            f"{BASE_URL}/3/invoices/{self.fortnox_ref}"
        )

        if fortnox_invoice := fortnox_res.get('Invoice'):
            self._fortnox_update(fortnox_invoice)
        else:
            raise UserError(
                f"There is an issue with the Fortnox connection. "
                f"Contact administrator. Response: {fortnox_res}"
            )

    def _fortnox_update(self, fortnox_invoice):
        """Update invoice with data from Fortnox."""
        self.ensure_one()

        self.fortnox_ref = fortnox_invoice["DocumentNumber"]

        # Ensure company context for partner fortnox_ref (company_dependent field)
        partner = self.partner_id.commercial_partner_id.with_company(self.company_id)
        partner.fortnox_ref = fortnox_invoice["CustomerNumber"]

        self.is_move_sent = True
        self._push_invoice_files()

    def _fortnox_create(self):
        """Create invoice in Fortnox."""
        self.ensure_one()

        if self.tax_included_in_price == "mixed":
            raise UserError(
                "Fortnox does not support having a mix of invoice lines where the tax is or is not "
                "included in the price. Please redo the lines so that all are tax included or all "
                "tax excluded from the price before syncing to Fortnox."
            )

        if not self.invoice_date_due:
            raise UserError(_("ERROR: missing date_due on invoice."))

        # Ensure company context for partner operations
        partner = self.partner_id.commercial_partner_id.with_company(self.company_id)

        if not partner.fortnox_ref:
            self.partner_id.with_company(self.company_id).partner_create(self.company_id)

        # Refresh partner to get updated fortnox_ref
        partner = self.partner_id.commercial_partner_id.with_company(self.company_id)
        if partner.fortnox_ref:
            self.partner_id.with_company(self.company_id).partner_update(self.company_id)

        invoice_lines = self._prepare_fortnox_invoice_lines()

        response = self.company_id.fortnox_request(
            'POST',
            "https://api.fortnox.se/3/invoices",
            data={
                "Invoice": self._prepare_fortnox_invoice_vals(invoice_lines)
            }
        )

        if response.get('ErrorInformation'):
            self._message_log(
                body=f"Error Creating Invoice Fortnox: {response['ErrorInformation']['message']}",
                subject='Fortnox Error'
            )
            _logger.error(f"{self.partner_id.name} has problem in its contact information, please check it")
        else:
            self.fortnox_ref = response["Invoice"]["DocumentNumber"]
            self.is_move_sent = True
            self.is_sent_to_fortnox = True
            self._push_invoice_files()

    def _prepare_fortnox_invoice_lines(self):
        """Prepare invoice lines for Fortnox API."""
        self.ensure_one()
        invoice_lines = []

        # Sort invoice lines and get them with correct language
        sorted_lines = sorted(
            self.with_context({'lang': self.partner_id.lang}).invoice_line_ids,
            key=lambda x: x.sequence
        )

        for line in sorted_lines:
            # Update product article in Fortnox if needed
            if line.product_id:
                line.product_id.with_company(self.company_id).article_update(self.company_id)

            line_name = self._format_line_description(line.name)

            if line.product_id:
                invoice_lines.append({
                    "AccountNumber": line.account_id.code,
                    "DeliveredQuantity": line.quantity,
                    "Unit": line.product_uom_id.name if line.product_uom_id else "",
                    "Description": line_name,
                    "ArticleNumber": line.product_id.default_code,
                    "Price": line.price_unit,
                    "VAT": int(line.tax_ids.mapped('amount')[0]) if len(line.tax_ids) > 0 else "",
                })
            else:
                # This is a note or similar - split if too long
                text_chunks = split_into_chunks(line_name, 255)
                for text in text_chunks:
                    invoice_lines.append({
                        "AccountNumber": 0,
                        "DeliveredQuantity": 0,
                        "Description": text,
                        "ArticleNumber": "",
                        "Price": 0,
                        "VAT": 0,
                    })

        return invoice_lines

    def _format_line_description(self, name):
        """Format line description for Fortnox."""
        if len(name.split(' ')) == 2:
            return name.split(' ')[1]
        return name.replace('[', '').replace(']', '').strip()

    def _prepare_fortnox_invoice_vals(self, invoice_lines):
        """Prepare invoice values for Fortnox API."""
        self.ensure_one()

        self._validate_fortnox_requirements()

        # Ensure partner is in correct company context
        partner = self.partner_id.commercial_partner_id.with_company(self.company_id)

        source_orders = self.line_ids.sale_line_ids.order_id if self.line_ids.sale_line_ids else False
        order_refs = self._get_order_references(source_orders)
        order_contact = source_orders[0].partner_id if source_orders else None

        commitment_date = self._get_commitment_date()
        yourreference = self._get_your_reference(order_contact)

        invoice_vals = {
            "Comments": "",
            "VATIncluded": self.tax_included_in_price == "tax_included_price",
            "Currency": self.currency_id.name,
            "CustomerName": partner.name,
            "CustomerNumber": partner.fortnox_ref,
            "DueDate": self.invoice_date_due.strftime('%Y-%m-%d'),
            "InvoiceDate": self.invoice_date.strftime(
                '%Y-%m-%d') if self.invoice_date else fields.Date.today().strftime('%Y-%m-%d'),
            "InvoiceRows": invoice_lines,
            "InvoiceType": "INVOICE",
            "Remarks": "",
            "Language": "SV" if self.partner_id.lang == "sv_SE" else "EN",
            "Country": partner.country_id.name if partner.country_id else "",
            "DeliveryAddress1": self.partner_shipping_id.street if self.partner_shipping_id and self.partner_shipping_id.street else "",
            "DeliveryAddress2": self.partner_shipping_id.street2 if self.partner_shipping_id and self.partner_shipping_id.street2 else "",
            "DeliveryCity": self.partner_shipping_id.city if self.partner_shipping_id and self.partner_shipping_id.city else "",
            "DeliveryCountry": self.partner_shipping_id.country_id.name if self.partner_shipping_id and self.partner_shipping_id.country_id else "",
            "DeliveryName": self.partner_shipping_id.name if self.partner_shipping_id and self.partner_shipping_id.name else "",
            "DeliveryZipCode": self.partner_shipping_id.zip if self.partner_shipping_id and self.partner_shipping_id.zip else "",
            "TermsOfDelivery": self.invoice_incoterm_id.fortnox_code if self.invoice_incoterm_id else "",
            "TermsOfPayment": self.invoice_payment_term_id.fortnox_code if self.invoice_payment_term_id else "",
            "OurReference": order_refs if order_refs else "",
            "YourReference": yourreference,
            "YourOrderNumber": self.ref if self.ref else "",
            "Freight": 0,
            "AdministrationFee": 0,
            "DeliveryDate": commitment_date
        }

        _logger.debug(f"Prepared Fortnox invoice values: {invoice_vals}")
        return invoice_vals

    def _validate_fortnox_requirements(self):
        """Validate required Fortnox codes are present."""
        if self.invoice_payment_term_id and not self.invoice_payment_term_id.fortnox_code:
            raise UserError(
                f"The payment term chosen ({self.invoice_payment_term_id.name}) is missing a Fortnox code. "
                f"Please add it."
            )

        if self.invoice_incoterm_id and not self.invoice_incoterm_id.fortnox_code:
            raise UserError(
                f"The Incoterm chosen ({self.invoice_incoterm_id.name}) is missing a Fortnox code. "
                f"Please add it."
            )

    def _get_order_references(self, source_orders):
        """Get comma-separated order references."""
        if not source_orders:
            return False
        return ", ".join(order.name for order in source_orders)

    def _get_commitment_date(self):
        """Get commitment date from sale order."""
        if self.line_ids.sale_line_ids.order_id:
            last_order = self.line_ids.sale_line_ids.order_id[-1]
            if last_order.commitment_date:
                return last_order.commitment_date.strftime('%Y-%m-%d')
        return ""

    def _get_your_reference(self, order_contact):
        """Get 'Your Reference' field value."""
        if self.partner_id.name and self.partner_id.type == "contact":
            return self.partner_id.name
        if order_contact and order_contact.name and order_contact.type == "contact":
            return order_contact.name
        return ""

    def _push_invoice_files(self):
        """Upload invoice attachments to Fortnox."""
        self.ensure_one()

        for attachment in self.attachment_ids:
            attachment._upload_file_to_fortnox(self.company_id)

            if attachment.fortnox_file_url:
                response = self.company_id.fortnox_request(
                    'POST',
                    "https://api.fortnox.se/api/fileattachments/attachments-v1",
                    data=[{
                        "entityId": int(self.fortnox_ref),
                        "entityType": "F",
                        "fileId": attachment.fortnox_file_archive_id,
                        "includeOnSend": True
                    }]
                )
                _logger.info(f"File upload result: {response}")


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    is_fortnox = fields.Boolean(string='Fortnox', default=True)

    def send_and_print_action(self):
        """Override normal send_and_print_action with Fortnox functionality."""
        res = super(AccountMoveSend, self).send_and_print_action()

        if self.is_fortnox:
            for invoice in self.invoice_ids:
                invoice.remove_zero_cost_lines()
                invoice.sync_fortnox()
                # Rate limiting to avoid spamming Fortnox API
                time.sleep(1)
        return res