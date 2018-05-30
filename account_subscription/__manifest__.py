# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2018 Vertel AB (<http://vertel.se>).
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
    'name' : 'Account Subscription',
    'version' : '1.0',
    'summary': 'Account Subscription',
    'description': """
Account Subscription
=====================
    """,
    'category': 'Accounting',
    'author': 'Vertel AB',
    'website': 'http://www.vertel.se',
    'images' : [],
    'depends' : ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_view.xml',
        'wizard/account_subscription_generate_view.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
