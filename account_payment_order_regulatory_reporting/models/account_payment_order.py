# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2017 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import api, fields, models, _, exceptions
from odoo.osv import expression
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import Warning
from odoo.exceptions import UserError
from lxml import etree

import logging

_logger = logging.getLogger(__name__)


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def generate_payment_file(self):  # noqa: C901 
        """Creates the SEPA Credit Transfer file. That's the important code!"""
        self.ensure_one()
        if self.payment_method_id.code != "sepa_credit_transfer":
            return super().generate_payment_file()

        pain_flavor = self.payment_method_id.pain_version
        # We use pain_flavor.startswith('pain.001.001.xx')
        # to support country-specific extensions such as
        # pain.001.001.03.ch.02 (cf l10n_ch_sepa)
        if not pain_flavor:
            raise UserError(_("PAIN version '%s' is not supported.") % pain_flavor)
        if pain_flavor.startswith("pain.001.001.02"):
            bic_xml_tag = "BIC"
            name_maxsize = 70
            root_xml_tag = "pain.001.001.02"
        elif pain_flavor.startswith("pain.001.001.03"):
            bic_xml_tag = "BIC"
            # size 70 -> 140 for <Nm> with pain.001.001.03
            # BUT the European Payment Council, in the document
            # "SEPA Credit Transfer Scheme Customer-to-bank
            # Implementation guidelines" v6.0 available on
            # http://www.europeanpaymentscouncil.eu/knowledge_bank.cfm
            # says that 'Nm' should be limited to 70
            # so we follow the "European Payment Council"
            # and we put 70 and not 140
            name_maxsize = 70
            root_xml_tag = "CstmrCdtTrfInitn"
        elif pain_flavor.startswith("pain.001.001.04"):
            bic_xml_tag = "BICFI"
            name_maxsize = 140
            root_xml_tag = "CstmrCdtTrfInitn"
        elif pain_flavor.startswith("pain.001.001.05"):
            bic_xml_tag = "BICFI"
            name_maxsize = 140
            root_xml_tag = "CstmrCdtTrfInitn"
        # added pain.001.003.03 for German Banks
        # it is not in the offical ISO 20022 documentations, but nearly all
        # german banks are working with this instead 001.001.03
        elif pain_flavor == "pain.001.003.03":
            bic_xml_tag = "BIC"
            name_maxsize = 70
            root_xml_tag = "CstmrCdtTrfInitn"
        else:
            raise UserError(_("PAIN version '%s' is not supported.") % pain_flavor)
        xsd_file = self.payment_method_id.get_xsd_file_path()
        gen_args = {
            "bic_xml_tag": bic_xml_tag,
            "name_maxsize": name_maxsize,
            "convert_to_ascii": self.payment_method_id.convert_to_ascii,
            "payment_method": "TRF",
            "file_prefix": "sct_",
            "pain_flavor": pain_flavor,
            "pain_xsd_file": xsd_file,
        }
        nsmap = self.generate_pain_nsmap()
        attrib = self.generate_pain_attrib()
        xml_root = etree.Element("Document", nsmap=nsmap, attrib=attrib)
        pain_root = etree.SubElement(xml_root, root_xml_tag)
        # A. Group header
        header = self.generate_group_header_block(pain_root, gen_args)
        group_header, nb_of_transactions_a, control_sum_a = header
        transactions_count_a = 0
        amount_control_sum_a = 0.0
        lines_per_group = {}
        # key = (requested_date, priority, local_instrument, categ_purpose)
        # values = list of lines as object
        for line in self.bank_line_ids:
            priority = line.priority
            local_instrument = line.local_instrument
            categ_purpose = line.category_purpose
            # The field line.date is the requested payment date
            # taking into account the 'date_prefered' setting
            # cf account_banking_payment_export/models/account_payment.py
            # in the inherit of action_open()
            key = (line.date, priority, local_instrument, categ_purpose)
            if key in lines_per_group:
                lines_per_group[key].append(line)
            else:
                lines_per_group[key] = [line]
        for (requested_date, priority, local_instrument, categ_purpose), lines in list(
                lines_per_group.items()
        ):
            # B. Payment info
            requested_date = fields.Date.to_string(requested_date)
            (
                payment_info,
                nb_of_transactions_b,
                control_sum_b,
            ) = self.generate_start_payment_info_block(
                pain_root,
                "self.name + '-' "
                "+ requested_date.replace('-', '')  + '-' + priority + "
                "'-' + local_instrument + '-' + category_purpose",
                priority,
                local_instrument,
                categ_purpose,
                False,
                requested_date,
                {
                    "self": self,
                    "priority": priority,
                    "requested_date": requested_date,
                    "local_instrument": local_instrument or "NOinstr",
                    "category_purpose": categ_purpose or "NOcateg",
                },
                gen_args,
            )
            self.generate_party_block(
                payment_info, "Dbtr", "B", self.company_partner_bank_id, gen_args
            )
            charge_bearer = etree.SubElement(payment_info, "ChrgBr")
            if self.sepa:
                charge_bearer_text = "SLEV"
            else:
                charge_bearer_text = self.charge_bearer
            charge_bearer.text = charge_bearer_text
            transactions_count_b = 0
            amount_control_sum_b = 0.0
            for line in lines:
                transactions_count_a += 1
                transactions_count_b += 1
                # C. Credit Transfer Transaction Info
                credit_transfer_transaction_info = etree.SubElement(
                    payment_info, "CdtTrfTxInf"
                )
                payment_identification = etree.SubElement(
                    credit_transfer_transaction_info, "PmtId"
                )
                instruction_identification = etree.SubElement(
                    payment_identification, "InstrId"
                )
                instruction_identification.text = self._prepare_field(
                    "Instruction Identification",
                    "line.name",
                    {"line": line},
                    35,
                    gen_args=gen_args,
                )
                end2end_identification = etree.SubElement(
                    payment_identification, "EndToEndId"
                )
                end2end_identification.text = self._prepare_field(
                    "End to End Identification",
                    "line.name",
                    {"line": line},
                    35,
                    gen_args=gen_args,
                )
                currency_name = self._prepare_field(
                    "Currency Code",
                    "line.currency_id.name",
                    {"line": line},
                    3,
                    gen_args=gen_args,
                )
                amount = etree.SubElement(credit_transfer_transaction_info, "Amt")
                instructed_amount = etree.SubElement(
                    amount, "InstdAmt", Ccy=currency_name
                )
                instructed_amount.text = "%.2f" % line.amount_currency
                amount_control_sum_a += line.amount_currency
                amount_control_sum_b += line.amount_currency
                if not line.partner_bank_id:
                    raise UserError(
                        _(
                            "Bank account is missing on the bank payment line "
                            "of partner '%s' (reference '%s')."
                        )
                        % (line.partner_id.name, line.name)
                    )
                self.generate_party_block(
                    credit_transfer_transaction_info,
                    "Cdtr",
                    "C",
                    line.partner_bank_id,
                    gen_args,
                    line,
                )
                #################################ADDITIONS
                for amt in credit_transfer_transaction_info.findall('Amt'):
                    InstdAmt_xml = amt.find('InstdAmt')
                    if InstdAmt_xml.attrib.get(
                            'Ccy') != 'SEK' and self.env.company.country_code == 'SE' and line.amount_company_currency >= 150000:

                        if not line.regulatory_reporting_code:
                            error_args = {"line_partner": line.partner_id.name,
                                          "line_communication": line.communication,
                                          "line_amount": line.amount_company_currency}
                            raise UserError(_("Regulatory Reporting Code is missing in a line\n\n"
                                              "{line_partner} {line_communication} \n\n"
                                              "Regulatory Reporting Code is required when the currency is EUR and when the value ({line_amount}) is greater or equal to 150000 SEK\n\n"
                                              "This important when making bank files").format(**error_args))

                        regulatory_reporting = etree.SubElement(credit_transfer_transaction_info, "RgltryRptg")
                        debit_credit_reporting_indicator = etree.SubElement(regulatory_reporting, "DbtCdtRptgInd")
                        # ~ if self.sepa:
                        debit_credit_reporting_indicator.text = "DEBT"
                        # ~ else:
                        # ~ debit_credit_reporting_indicator.text = self.charge_bearer

                        authority = etree.SubElement(regulatory_reporting, "Authrty")
                        authority_name = etree.SubElement(authority, "Nm")
                        authority_name.text = "TEST NAME"
                        country = etree.SubElement(authority, "Ctry")
                        country.text = self.env.company.country_code

                        details = etree.SubElement(regulatory_reporting, "Dtls")
                        details_country = etree.SubElement(details, "Ctry")
                        details_country.text = self.env.company.country_code
                        details_code = etree.SubElement(details, "Cd")

                        details_code.text = line.regulatory_reporting_code.code
                        break
                #################################ADDITIONS
                if line.purpose:
                    purpose = etree.SubElement(credit_transfer_transaction_info, "Purp")
                    etree.SubElement(purpose, "Cd").text = line.purpose
                self.generate_remittance_info_block(
                    credit_transfer_transaction_info, line, gen_args
                )
            if not pain_flavor.startswith("pain.001.001.02"):
                nb_of_transactions_b.text = str(transactions_count_b)
                control_sum_b.text = "%.2f" % amount_control_sum_b
        if not pain_flavor.startswith("pain.001.001.02"):
            nb_of_transactions_a.text = str(transactions_count_a)
            control_sum_a.text = "%.2f" % amount_control_sum_a
        else:
            nb_of_transactions_a.text = str(transactions_count_a)
            control_sum_a.text = "%.2f" % amount_control_sum_a
        return self.finalize_sepa_file_creation(xml_root, gen_args)

    # ~ def draft2open(self):
    # ~ """
    # ~ Called when you click on the 'Confirm' button
    # ~ Set the 'date' on payment line depending on the 'date_prefered'
    # ~ setting of the payment.order
    # ~ Re-generate the bank payment lines
    # ~ """
    # ~ bplo = self.env["bank.payment.line"]
    # ~ today = fields.Date.context_today(self)
    # ~ for order in self:
    # ~ if not order.journal_id:
    # ~ raise UserError(
    # ~ _("Missing Bank Journal on payment order %s.") % order.name
    # ~ )
    # ~ if (
    # ~ order.payment_method_id.bank_account_required
    # ~ and not order.journal_id.bank_account_id
    # ~ ):
    # ~ raise UserError(
    # ~ _("Missing bank account on bank journal '%s'.")
    # ~ % order.journal_id.display_name
    # ~ )
    # ~ if not order.payment_line_ids:
    # ~ raise UserError(
    # ~ _("There are no transactions on payment order %s.") % order.name
    # ~ )
    # ~ # Delete existing bank payment lines
    # ~ order.bank_line_ids.unlink()
    # ~ # Create the bank payment lines from the payment lines
    # ~ group_paylines = {}  # key = hashcode
    # ~ for payline in order.payment_line_ids:
    # ~ payline.draft2open_payment_line_check()
    # ~ # Compute requested payment date
    # ~ if order.date_prefered == "due":
    # ~ requested_date = payline.ml_maturity_date or payline.date or today
    # ~ elif order.date_prefered == "fixed":
    # ~ requested_date = order.date_scheduled or today
    # ~ else:
    # ~ requested_date = today
    # ~ # No payment date in the past
    # ~ if requested_date < today:
    # ~ requested_date = today
    # ~ # inbound: check option no_debit_before_maturity
    # ~ if (
    # ~ order.payment_type == "inbound"
    # ~ and order.payment_mode_id.no_debit_before_maturity
    # ~ and payline.ml_maturity_date
    # ~ and requested_date < payline.ml_maturity_date
    # ~ ):
    # ~ raise UserError(
    # ~ _(
    # ~ "The payment mode '%s' has the option "
    # ~ "'Disallow Debit Before Maturity Date'. The "
    # ~ "payment line %s has a maturity date %s "
    # ~ "which is after the computed payment date %s."
    # ~ )
    # ~ % (
    # ~ order.payment_mode_id.name,
    # ~ payline.name,
    # ~ payline.ml_maturity_date,
    # ~ requested_date,
    # ~ )
    # ~ )
    # ~ # Write requested_date on 'date' field of payment line
    # ~ # norecompute is for avoiding a chained recomputation
    # ~ # payment_line_ids.date
    # ~ # > payment_line_ids.amount_company_currency
    # ~ # > total_company_currency
    # ~ with self.env.norecompute():
    # ~ payline.date = requested_date
    # ~ # Group options
    # ~ if order.payment_mode_id.group_lines:
    # ~ hashcode = payline.payment_line_hashcode()
    # ~ else:
    # ~ # Use line ID as hascode, which actually means no grouping
    # ~ hashcode = payline.id
    # ~ if hashcode in group_paylines:
    # ~ group_paylines[hashcode]["paylines"] += payline
    # ~ group_paylines[hashcode]["total"] += payline.amount_currency
    # ~ else:
    # ~ group_paylines[hashcode] = {
    # ~ "paylines": payline,
    # ~ "total": payline.amount_currency,
    # ~ }
    # ~ order.recompute()
    # ~ # Create bank payment lines
    # ~ for paydict in list(group_paylines.values()):
    # ~ # Block if a bank payment line is <= 0
    # ~ if paydict["total"] <= 0:
    # ~ raise UserError(
    # ~ _("The amount for Partner '%s' is negative " "or null (%.2f) !")
    # ~ % (paydict["paylines"][0].partner_id.name, paydict["total"])
    # ~ )
    # ~ vals = self._prepare_bank_payment_line(paydict["paylines"])
    # ~ bplo.create(vals)
    # ~ self.write({"state": "open"})
    # ~ return True
