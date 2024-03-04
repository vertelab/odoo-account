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
    'name': 'Account Analytic Extended',
    'version': '16.0.0.0.1',
    'summary': 'Account Analytic Extended',
    'category': 'Accounting',
    'description': """
        Account Analytic Extended.
    """,
    'sequence': '20',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_analytic_extended',
    'images': ['/static/description/banner.png'],  # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'depends': ['account_financial_report', 'account'],
    'data': [
        'views/account_move_line.xml'
    ],
    'qweb': [],
    'installable': True,
}
