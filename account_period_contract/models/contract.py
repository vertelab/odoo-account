import logging

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tests import Form
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class Contract(models.Model):
    _inherit = "contract.contract"

    def _get_default_period_id(self, date_invoice):
        return self.env['account.period'].date2period(date_invoice or fields.Date.today()).id

    def _prepare_invoice(self, date_invoice, journal=None):
        if not self._get_default_period_id(date_invoice):
            raise UserError(_(f"No valid period within the invoice date - {date_invoice}"))
        """Prepare in a Form the values for the generated invoice record.

        :return: A tuple with the vals dictionary and the Form with the
          preloaded values for being used in lines.
        """
        self.ensure_one()
        if not journal:
            journal = (
                self.journal_id
                if self.journal_id.type == self.contract_type
                else self.env["account.journal"].search(
                    [
                        ("type", "=", self.contract_type),
                        ("company_id", "=", self.company_id.id),
                    ],
                    limit=1,
                )
            )
        if not journal:
            raise ValidationError(
                _("Please define a %s journal for the company '%s'.")
                % (self.contract_type, self.company_id.name or "")
            )
        invoice_type = "out_invoice"
        if self.contract_type == "purchase":
            invoice_type = "in_invoice"
        move_form = Form(
            self.env["account.move"]
            .with_company(self.company_id)
            .with_context(default_move_type=invoice_type, default_name="/")
        )
        move_form.partner_id = self.invoice_partner_id
        if self.payment_term_id:
            move_form.invoice_payment_term_id = self.payment_term_id
        if self.fiscal_position_id:
            move_form.fiscal_position_id = self.fiscal_position_id
        invoice_vals = move_form._values_to_save(all_fields=True)
        invoice_vals.update(
            {
                "ref": self.code,
                "company_id": self.company_id.id,
                "currency_id": self.currency_id.id,
                "invoice_date": date_invoice,
                "journal_id": journal.id,
                "invoice_origin": self.name,
                "invoice_user_id": self.user_id.id,
                "period_id": self._get_default_period_id(date_invoice)
            }
        )
        return invoice_vals, move_form
