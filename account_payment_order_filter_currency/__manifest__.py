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
    'name': 'Account: Payment Filter Currency',
    'version': '14.0.0.0.1',
    'summary': 'Adds the capability to filter payment order lines based on currency',
    'category': 'Accounting',
    'author': 'Vertel AB',
    'images': ['/static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'description': """
        There is a new filed on the payment order wizard that is used to find invoice lines.
	This new field allowes us to find invoice lines for a specific currency.
    """,
    'depends': ['account_payment_order'],
    'data': [
        'views/account_payment_line_create_view.xml',
        'views/res_partner_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
