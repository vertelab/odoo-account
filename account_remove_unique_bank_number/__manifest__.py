# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) {year} {company} (<{mail}>)
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
    'name': 'Account: Relax Constraints on Unique Bank Number',
    'version': '14.0.0.1.0',
    'summary': 'Relax Constraints on Unique Bank Number',
    'category': 'Accounting',
    'description': """
        Relax Constraints on Unique Bank Number.
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_remove_unique_bank_number',
    'images': ['static/description/banner.png'],  # 560x280 px.
    'license': 'AGPL-3',
    'depends': ['base'],
    'data': [
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
