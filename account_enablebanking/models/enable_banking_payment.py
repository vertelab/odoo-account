# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class EnableBankingPayment(models.Model):
    _name = "enable.banking.payment"
    _description = "Enable Banking Payment"
    _order = "create_date desc"
    _inherit = ["mail.thread"]

    name = fields.Char(
        string="Reference",
        compute="_compute_name", store=True,
    )
    journal_id = fields.Many2one(
        string="Journal",
        comodel_name="account.journal",
        required=True,
        domain=[("type", "=", "bank")],
    )
    payment_order_id = fields.Many2one(
        string="Payment Order",
        comodel_name="account.payment.order",
        help="The Odoo payment order this payment was created from.",
    )
    enable_banking_payment_id = fields.Char(
        string="Enable Banking Payment ID",
        readonly=True,
        help="The payment ID assigned by Enable Banking API.",
    )
    redirect_url = fields.Char(
        string="Redirect URL",
        readonly=True,
        help="The URL where the user must be redirected to authorize the payment.",
    )
    state = fields.Selection(
        string="Status",
        selection=[
            ("draft", "Draft"),
            ("pending_authorization", "Pending Authorization"),
            ("authorized", "Authorized"),
            ("submitted", "Submitted"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
    )
    amount = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        string="Currency",
        comodel_name="res.currency",
        related="journal_id.currency_id",
        store=True,
    )
    creditor_name = fields.Char(string="Creditor Name")
    creditor_iban = fields.Char(string="Creditor IBAN")
    creditor_bic = fields.Char(string="Creditor BIC")
    remittance_info = fields.Char(string="Remittance Information")
    payment_count = fields.Integer(
        string="Number of Payments",
        default=1,
    )
    response_data = fields.Json(
        string="API Response",
        readonly=True,
    )
    error_message = fields.Char(
        string="Error",
        readonly=True,
    )
    sent_date = fields.Datetime(
        string="Sent Date",
        readonly=True,
    )
    company_id = fields.Many2one(
        string="Company",
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    aspsp_id = fields.Char(
        string="ASPSP ID",
        help="The bank/ASPSP identifier for payment routing.",
    )

    @api.depends("journal_id", "create_date")
    def _compute_name(self):
        for rec in self:
            if rec.journal_id:
                date_str = rec.create_date.strftime("%Y%m%d") if rec.create_date else ""
                rec.name = f"EB-PAY-{rec.journal_id.code}-{date_str}-{rec.id}"
            else:
                rec.name = f"EB-PAY-{rec.id}"

    def action_send_to_bank(self):
        """Send the payment to Enable Banking API."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Payment can only be sent when in draft state."))

        partner_id = self.journal_id.bank_id.api_contact_integration
        if not partner_id:
            raise UserError(_("No API contact configured for bank %s.", self.journal_id.bank_id.name))

        api_url, private_key, application_id, base_headers = partner_id.request_essentials()

        # Build payment request
        payment_data = {
            "payment_type": "SEPA_CREDIT_TRANSFER",
            "creditor": {
                "name": self.creditor_name or self.journal_id.company_id.name,
                "account": {"iban": self.creditor_iban or self.journal_id.bank_account_id.acc_number},
            },
            "instructed_amount": {
                "currency": self.currency_id.name,
                "amount": str(self.amount),
            },
            "remittance_information": self.remittance_info or "",
            "redirect_url": self._get_redirect_url(),
        }

        if self.aspsp_id:
            payment_data["aspsp_id"] = self.aspsp_id

        _logger.info("Sending payment to Enable Banking: %s", payment_data)

        try:
            response = requests.post(
                f"{api_url}/payments",
                json=payment_data,
                headers=base_headers,
                timeout=30,
            )
        except Exception as e:
            self.write({
                "state": "rejected",
                "error_message": str(e),
            })
            _logger.exception("Failed to send payment to Enable Banking")
            raise UserError(_("Failed to send payment: %s", str(e)))

        if response.status_code in (200, 201):
            resp_data = response.json()
            self.write({
                "enable_banking_payment_id": resp_data.get("payment_id"),
                "redirect_url": resp_data.get("redirect_url"),
                "state": "pending_authorization",
                "response_data": resp_data,
                "sent_date": fields.Datetime.now(),
            })

            # Return action to redirect user or show status
            if self.redirect_url:
                return {
                    "type": "ir.actions.act_url",
                    "url": self.redirect_url,
                    "target": "new",
                }
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get("message", response.text)
            except Exception:
                error_msg = response.text

            self.write({
                "state": "rejected",
                "error_message": error_msg,
                "response_data": response.text,
            })
            raise UserError(_("Enable Banking API error: %s", error_msg))

    def action_check_status(self):
        """Check payment status from Enable Banking API."""
        self.ensure_one()
        if not self.enable_banking_payment_id:
            raise UserError(_("No Enable Banking payment ID available."))

        partner_id = self.journal_id.bank_id.api_contact_integration
        api_url, private_key, application_id, base_headers = partner_id.request_essentials()

        try:
            response = requests.get(
                f"{api_url}/payments/{self.enable_banking_payment_id}",
                headers=base_headers,
                timeout=30,
            )
        except Exception as e:
            raise UserError(_("Failed to check payment status: %s", str(e)))

        if response.status_code == 200:
            resp_data = response.json()
            payment_status = resp_data.get("payment_status", "")
            _logger.info("Payment %s status: %s", self.enable_banking_payment_id, payment_status)

            status_mapping = {
                "ACCEPTED": "accepted",
                "ACCP": "accepted",
                "ACTC": "accepted",
                "ACWC": "accepted",
                "AUTHORISED": "authorized",
                "AUTH": "authorized",
                "PENDING": "pending_authorization",
                "PDNG": "pending_authorization",
                "REJECTED": "rejected",
                "RJCT": "rejected",
                "CANCELLED": "cancelled",
                "CANC": "cancelled",
            }

            new_state = status_mapping.get(payment_status, "pending_authorization")
            self.write({
                "state": new_state,
                "response_data": resp_data,
            })

            if new_state == "accepted":
                self.message_post(body=_("Payment accepted by bank."))
            elif new_state == "rejected":
                reason = resp_data.get("rejection_reason", "Unknown reason")
                self.message_post(body=_("Payment rejected: %s", reason))
        else:
            raise UserError(_("API error: %s", response.text))

    def action_cancel(self):
        """Cancel the payment."""
        self.ensure_one()
        if self.state in ("accepted", "cancelled"):
            raise UserError(_("Cannot cancel a payment that is already %s.", self.state))

        if self.enable_banking_payment_id:
            partner_id = self.journal_id.bank_id.api_contact_integration
            api_url, private_key, application_id, base_headers = partner_id.request_essentials()

            try:
                response = requests.delete(
                    f"{api_url}/payments/{self.enable_banking_payment_id}",
                    headers=base_headers,
                    timeout=30,
                )
            except Exception as e:
                _logger.warning("Error cancelling payment: %s", e)

        self.write({"state": "cancelled"})

    def _get_redirect_url(self):
        """Get the callback URL for payment authorization redirect."""
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "http://localhost:8069")
        return f"{base_url}/account/enable-banking/payment-return"

    def _cron_check_payment_status(self):
        """Cron job to check status of pending payments."""
        payments = self.search([("state", "in", ("pending_authorization", "authorized"))])
        for payment in payments:
            try:
                payment.action_check_status()
            except Exception as e:
                _logger.error("Error checking payment %s: %s", payment.id, str(e))
