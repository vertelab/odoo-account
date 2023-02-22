# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2017 Vertel AB (<http://vertel.se>).
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name' : 'Account Period',
    'version' : '1.0',
    'summary': 'Account Period',
    'description': """
Account Period
==============
Added period for accounting
    """,
    'category': 'Accounting',
    'author': 'Vertel AB',
    'website': 'http://www.vertel.se',
    'images' : [],
    'depends' : ['account','payment'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/account_period_close_view.xml',
        'wizard/account_period_create_view.xml',
        'wizard/account_fiscalyear_close_view.xml',
        'views/account_view.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
