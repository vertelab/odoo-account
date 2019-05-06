# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi, Guewen Baconnier
#    Copyright Camptocamp SA 2011
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

from openerp.report import report_sxw
from openerp.addons.account_financial_report_webkit.report.webkit_parser_header_fix import HeaderFooterTextWebKitParser
from openerp.addons.account_financial_report_webkit.report.open_invoices import PartnersOpenInvoicesWebkit
import logging
_logger = logging.getLogger(__name__)

class PartnersOpenInvoicesWebkit(PartnersOpenInvoicesWebkit):

    def set_context(self, objects, data, ids, report_type=None):
        """Populate a ledger_lines attribute on each browse record that will
           be used by mako template"""

        self.account_selection_ids = self._get_form_param('accounts_ids', data)

        return super(PartnersOpenInvoicesWebkit, self).set_context(
            objects, data, ids, report_type=report_type)
            
    def get_all_accounts(self, account_ids, exclude_type=None, only_type=None,
                         filter_report_type=None, context=None):

        return self.account_selection_ids or super(PartnersOpenInvoicesWebkit, self).get_all_accounts(account_ids, exclude_type, only_type,
                         filter_report_type, context)

report_parser = HeaderFooterTextWebKitParser(
    'report.account.account_report_open_invoices_webkit',
    'account.account',
    'addons/account_financial_report_webkit/report/templates/\
                                        account_report_open_invoices.mako',
    parser=PartnersOpenInvoicesWebkit,
    register = False)
report_parser._reports['report.account.account_report_open_invoices_webkit'] = report_parser
