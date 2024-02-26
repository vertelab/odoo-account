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
#
# https://www.odoo.com/documentation/14.0/reference/module.html
#
{
    'name': 'Groups to Manage Account Move Types',
    'version': '16.0.0.0.0',
    'summary': """
        Groups to Manage Account Move Types    
    """,
    'category': '', # Technical Settings|Localization|Payroll Localization|Account Charts|User types|Invoicing|Sales|Human Resources|Operations|Marketing|Manufacturing|Website|Theme|Administration|Appraisals|Sign|Helpdesk|Administration|Extra Rights|Other Extra Rights|
    'description': """
        Groups to Manage Account Move Types
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-',
    'license': 'AGPL-3',
    'depends': ['account', 'account_period_vrtl'],
    'data': [
        'security/security.xml',
        # 'views/menu.xml',
        'views/account_view.xml',
    ],
    'demo': [],
    'application': False,
    'installable': True,
    'auto_install': False,
}