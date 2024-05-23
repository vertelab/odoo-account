# © 2016-2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models, _
from odoo.exceptions import UserError
from lxml import etree
import logging

logger = logging.getLogger(__name__)


class BaseUbl(models.AbstractModel):
    _inherit = 'base.ubl'

    @api.model
    def _ubl_add_payment_means(
            self, partner_bank, payment_mode, date_due, parent_node, ns,
            payment_identifier=None, version='2.1'):
                
        res_id = self.env.context.get('params', {}).get('id')
        res_model = self.env.context.get('params', {}).get('model')
        res_obj = self.env[res_model].search([('id', '=', res_id)], limit=1) 
        if res_id:

            payee_fin_account_value = self.env['ir.config_parameter'].sudo().get_param('payee_fin_account_key')
            print(payee_fin_account_value)
            if not payee_fin_account_value:  # System parameter is missing
                raise UserError('Please create a system parameter with the key payee_fin_account_key')
            elif payee_fin_account_value == "False" or payee_fin_account_value == "0":
                # System parameter has a bad value
                raise UserError(
                    f"System parameter payee_fin_account_value can't be False or 0 ({payee_fin_account_value}) ")

            pay_means = etree.SubElement(parent_node, ns['cac'] + 'PaymentMeans')
            pay_means_code = etree.SubElement(
                pay_means, ns['cbc'] + 'PaymentMeansCode', name=payment_mode.payment_method_id.name or 'Electronic')
            pay_means_code.text = payment_mode.payment_method_id.unece_code or '30'
            # ~ pay_due_date = etree.SubElement(pay_means, ns['cbc'] + 'PaymentDueDate')
            # ~ pay_due_date.text = date_due.strftime('%Y-%m-%d')
            payment_id = etree.SubElement(pay_means, ns['cbc'] + 'PaymentID')
            payment_id.text = res_obj.payment_reference.split('/')[0] if res_obj.payment_reference else ''
            payee_fin_account = etree.SubElement(
                pay_means, ns['cac'] + 'PayeeFinancialAccount')
            payee_fin_account_id = etree.SubElement(payee_fin_account, ns['cbc'] + 'ID')
            payee_fin_account_id.text = payee_fin_account_value
            financial_inst_branch = etree.SubElement(payee_fin_account, ns['cac'] + 'FinancialInstitutionBranch')
            financial_inst_id = etree.SubElement(financial_inst_branch, ns['cbc'] + 'ID')
            financial_inst_id.text = 'SE:BANKGIRO'
