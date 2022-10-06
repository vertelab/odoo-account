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
    'name': 'Account: Analytic Tag: Area Of Responsability and Project Number',
    'version': '14.0.0.0.1',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Adds types on a analytic account tag, so that we can set two new fields on a journal line.',
    'category': 'Accounting',
    #'sequence': '1'
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_analytic_tag_responsability_project_no',
    'images': ['static/description/banner.png'], # 560x280 px
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'description': """
Account Analytic Tag: Area Of Responsability and Project Number
========================================================
Adds types on a analytic account tag, so that we can set two new fields on a journal line and a sale Order Line.
This done so that we can filter on Area of Responsability and Project Number fields. Which are set on an move line and a sale order line if the tags has either set as a type.
    """,
    'depends': ['analytic', 'account', 'sale', 'account_period', 'purchase'],
    'data': [
        'views/analytic_tag.xml',
        'views/account_move_line.xml',
        'views/sale_order_line.xml',
        'data/account_filter.xml',
        'data/res_config.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
