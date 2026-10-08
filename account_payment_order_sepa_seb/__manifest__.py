# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2021- Vertel Sverige AB (<https://vertel.se>).
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
    'name': 'Account: Payment Order Sepa SEB',
    'version': '18.0.1.1.0',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Fixes SEPA payment file errors for SEB.',
    'category': 'Accounting',
    #'sequence': '1'
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_payment_order_sepa_seb',
    'images': ['/static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'description': '''
Payment Order Sepa SEB
======================

    Fixes SEPA payment file errors for SEB.

    Features:

        - Extends Odoo: Builds on account.payment.order.
    ''',
#External Repo https://github.com/OCA/bank-payment
    'depends': ['account_banking_pain_base','account_banking_sepa_direct_debit','account_payment_order'],
    'data': [
        #'views/regulatory_reporting_code.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
