# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2021- Vertel AB (<https://vertel.se>)
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

{
    'name': 'Account Move Contact',
    'version': '14.0.0.0.0',
    'summary': "Adds a contact field on invoices.",
    'category': 'Accounting',
    'description': """
        Adds a contact person field on invoices which is related to the sale orders partner, and adds a many2one field on the invoice view that leads to the sale order.
    """,
    #'sequence': 1,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account',
    #'images': ['static/description/banner.png'], # 560x280
    'license': 'AGPL-3',
    'depends': ['account','sale'],
    'data': [
        'views/account_move.xml',
    ],
    'demo': [],
    'application': False,
    'installable': True,    
    'auto_install': False,
}
