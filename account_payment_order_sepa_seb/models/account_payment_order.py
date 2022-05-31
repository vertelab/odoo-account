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
from lxml import etree
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"
    
    
    @api.model
    def generate_initiating_party_block(self, parent_node, gen_args):
        my_company_name = self._prepare_field(
            "Company Name",
            "self.company_partner_bank_id.partner_id.name",
            {"self": self},
            gen_args.get("name_maxsize"),
            gen_args=gen_args,
        )

        initiating_party = etree.SubElement(parent_node, "InitgPty")
        initiating_party_name = etree.SubElement(initiating_party, "Nm")
        initiating_party_name.text = my_company_name
        initiating_party_identifier = (
            self.payment_mode_id.initiating_party_identifier
            or self.payment_mode_id.company_id.initiating_party_identifier
        )
        initiating_party_issuer = (
            self.payment_mode_id.initiating_party_issuer
            or self.payment_mode_id.company_id.initiating_party_issuer
        )

        initiating_party_scheme = (
            self.payment_mode_id.initiating_party_scheme
            or self.payment_mode_id.company_id.initiating_party_scheme
        )
        # in pain.008.001.02.ch.01.xsd files they use
        # initiating_party_identifier but not initiating_party_issuer
        if initiating_party_identifier:
            iniparty_id = etree.SubElement(initiating_party, "Id")
            iniparty_org_id = etree.SubElement(iniparty_id, "OrgId")
            iniparty_org_other = etree.SubElement(iniparty_org_id, "Othr")
            iniparty_org_other_id = etree.SubElement(iniparty_org_other, "Id")
            iniparty_org_other_id.text = initiating_party_identifier
            if initiating_party_scheme:
                iniparty_org_other_scheme = etree.SubElement(
                    iniparty_org_other, "SchmeNm"
                )
                iniparty_org_other_scheme_name = etree.SubElement(
                    iniparty_org_other_scheme, "Cd" ###### Used to be Prtry but the SEB parser gave an error and wanted Cd instead
                )
                iniparty_org_other_scheme_name.text = initiating_party_scheme
            if initiating_party_issuer:
                iniparty_org_other_issuer = etree.SubElement(iniparty_org_other, "Issr")
                iniparty_org_other_issuer.text = initiating_party_issuer
        elif self._must_have_initiating_party(gen_args):
            raise UserError(
                _(
                    "Missing 'Initiating Party Issuer' and/or "
                    "'Initiating Party Identifier' for the company '%s'. "
                    "Both fields must have a value."
                )
                % self.company_id.name
            )
        return True

    @api.model
    def generate_party_agent(
        self, parent_node, party_type, order, partner_bank, gen_args, bank_line=None
    ):
        # ~ logger.warning("generate_party_agent")
        # ~ logger.warning(f"{parent_node=}")
        # ~ logger.warning(f"{party_type=}")
        # ~ logger.warning(f"{partner_bank=}")
        # ~ logger.warning(f"{gen_args=}")
        # ~ logger.warning(f"{bank_line=}")
        """Generate the piece of the XML file corresponding to BIC
        This code is mutualized between TRF and DD
        Starting from Feb 1st 2016, we should be able to do
        cross-border SEPA transfers without BIC, cf
        http://www.europeanpaymentscouncil.eu/index.cfm/
        sepa-credit-transfer/iban-and-bic/
        In some localization (l10n_ch_sepa for example), they need the
        bank_line argument"""
        party_agent_institution = False
        logger.warning(f"{partner_bank=}")
        if partner_bank.bank_bic:
            party_agent = etree.SubElement(parent_node, "%sAgt" % party_type)
            logger.warning(f"party_agent:{party_agent.text}")
            party_agent_institution = etree.SubElement(party_agent, "FinInstnId")
            logger.warning(f"party_agent_institution:{party_agent_institution.text}")
            party_agent_bic = etree.SubElement(
                party_agent_institution, gen_args.get("bic_xml_tag")
            )
            party_agent_bic.text = partner_bank.bank_bic
            logger.warning(f"party_agent_bic:{party_agent_bic.text}")
        else:
            # New Comment: Seem like if if we have a ban giro account then we still need the 'Creditor Agent' block which is why i have added or order == "C" and re.match('\d{3,4}-\d{4}', partner_bank.acc_number)): to the if case
            if order == "B" or (order == "C" and gen_args["payment_method"] == "DD" or order == "C" and re.match('\d{3,4}-\d{4}', partner_bank.acc_number)):
                
                party_agent = etree.SubElement(parent_node, "%sAgt" % party_type)
                party_agent_institution = etree.SubElement(party_agent, "FinInstnId")
                
                if partner_bank.acc_number and re.match('\d{3,4}-\d{4}', partner_bank.acc_number):        ################################################################################################################### ADDIDTIONS
                    party_agent_extra_bank_giro1 = etree.SubElement(party_agent_institution, "ClrSysMmbId")
                    party_agent_extra_bank_giro2 = etree.SubElement(party_agent_extra_bank_giro1, "ClrSysId")
                    party_agent_extra_bank_giro3 = etree.SubElement(party_agent_extra_bank_giro2, "Cd")
                    party_agent_extra_bank_giro3.text = "SESBA"
                    party_agent_extra_bank_giro4 = etree.SubElement(party_agent_extra_bank_giro1, "MmbId")
                    party_agent_extra_bank_giro4.text = "9900"
                else: ################################################################################################################### ADDIDTIONS
                    party_agent_other = etree.SubElement(party_agent_institution, "Othr")
                    party_agent_other_identification = etree.SubElement(
                    party_agent_other, "Id"
                    )
                    party_agent_other_identification.text = "NOTPROVIDED"
            # for Credit Transfers, in the 'C' block, if BIC is not provided,
            # we should not put the 'Creditor Agent' block at all,
            # as per the guidelines of the EPC

            
        return True
        
        
    @api.model
    def generate_party_acc_number(
        self, parent_node, party_type, order, partner_bank, gen_args, bank_line=None
    ):
        party_account = etree.SubElement(parent_node, "%sAcct" % party_type)
        party_account_id = etree.SubElement(party_account, "Id")
        logger.warning("%sAcct" % party_type)
        if partner_bank.acc_type == "iban":
            party_account_iban = etree.SubElement(party_account_id, "IBAN")
            party_account_iban.text = partner_bank.sanitized_acc_number
        ################################################################################################ ADDIDTIONS
        else:
            party_account_other = etree.SubElement(party_account_id, "Othr")
            party_account_other_id = etree.SubElement(party_account_other, "Id")
            party_account_other_id.text = partner_bank.sanitized_acc_number
            if partner_bank.acc_number and re.match('\d{3,4}-\d{4}', partner_bank.acc_number) or partner_bank.acc_type == "bank_giro":
                party_account_other_schmenm = etree.SubElement(party_account_other, "SchmeNm")
                party_account_other_cd = etree.SubElement(party_account_other_schmenm, "Prtry")
                party_account_other_cd.text = "BGNR"
            else:
                party_account_other_schmenm = etree.SubElement(party_account_other, "SchmeNm")
                party_account_other_cd = etree.SubElement(party_account_other_schmenm, "Cd")
                party_account_other_cd.text = "BBAN"
                
     


