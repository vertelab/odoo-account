# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<https://vertel.se>).
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
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Account: Bokföring CE',
    'version': '1.0',
    # Version ledger: 17.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'License Manager.',
    'category': 'Accounting',
    'description': """
    Accounting for Community Edition
    
    This module depends on the following modules:
    
    Vertel
    vertelab/odoo-account/account_period_vrtl

    OCA
    https://github.com/OCA/account-financial-reporting/tree/17.0/account_financial_report
    https://github.com/OCA/account-reconcile/tree/17.0/account_reconcile_oca
    https://github.com/OCA/bank-statement-import/tree/17.0/account_statement_import_camt
    https://github.com/OCA/mis-builder/tree/17.0/mis_builder
    https://github.com/OCA/mis-builder/tree/17.0/mis_builder_budget

    account_banking_sepa_credit_transfer
    account_banking_sepa_direct_debit
    # account_bank_payment
    https://github.com/OCA/bank-payment
    
    https://pypi.org/project/Unidecode/
    pip3 install unidecode:
    root@odoo16server:~$ pip3 install Unidecode


    """,
    #'sequence': '1',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_accountant_ce',
    'images': ['static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'depends': [
        'sale',
        'account_financial_report',
        'account_reconcile_oca',
        'mis_builder', 
        'mis_builder_budget',
        'account_asset_management'
        #'account_period_vrtl',
        #'account_statement_import_camt',
        #'account_banking_sepa_credit_transfer',
    ],
    'data': [
	"security/ir.model.access.csv",
        "security/account_accountant_security.xml",
        "data/account_accountant_data.xml",
        "views/account_fiscal_year_view.xml",
        #"views/license_view.xml",
        #"views/agreement_view.xml",
        #"views/product_template_view.xml",
        #"data/cron_demo.xml",
    ],
    "demo": [
    ],
    'installable': True,
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
