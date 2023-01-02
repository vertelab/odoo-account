# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2021- Vertel AB (<https://vertel.se>).
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
    'name': 'Account: Regulatory Reporting Sweden',
    'version': '14.0.0.0.1',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Adds Account Regulatory Reporting for Sweden',
    'category': 'Accounting',
    #'sequence': '1'
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps',
    #'images': ['/static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'description': """

When making bank files, with international payments in Sweden, we are sometimes required  to add Account Regulatory Reporting to the generated file.
This is required, when the value of a of a payment is above 150 000 SEK.

This module adds a List of most commonly used Regulatory Reporting codes, which can be found in the config menu for invoicing.

When we make a sale order and try to make bank payment lines then it will require the user to add Regulatory Reporting codes if the value is above 150 000 SEK and if the currency is not SEK, at which point this module will assume that it is an international payment.

    """,
    'depends': ['account_banking_pain_base','account_payment_order'],
    'data': [
        'views/regulatory_reporting_code.xml',
        'data/regulatory_reporting_codes.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}


