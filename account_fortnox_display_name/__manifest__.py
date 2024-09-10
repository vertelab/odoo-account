# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2024- Vertel AB  info@vertel.se
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
#
# https://www.odoo.com/documentation/14.0/reference/module.html
#
{
    'name': 'Account: Fortnox Display Name',
    'version': '1.0',
    'summary': """
    Replaces name with the fortnox ref dash name if there is a fortnox ref
    """,
    'category': 'Accounting',
    'description': """
    Replaces name with the fortnox ref dash name if there is a fortnox ref
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_fortnox_display_name',
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'depends': ['account_fortnox'],
    'data': ['views/account_move_views.xml'],
    'demo': [],
    'application': False,
    'installable': True,    
    'auto_install': False,
}
