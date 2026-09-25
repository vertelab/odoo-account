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
    'version': '18.0.1.0.0',
    'summary': """Shows the Fortnox reference in the invoice display name.""",
    'category': 'Accounting',
    'description': '''
Fortnox Display Name
====================

    Replaces name with the fortnox ref dash name if there is a fortnox ref

    Features:

        - UI Integration: Extends 1 view(s) in the Odoo interface.
        - Extends Odoo: Builds on account.move.
    ''',
    'author': 'Vertel Sverige AB',
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
