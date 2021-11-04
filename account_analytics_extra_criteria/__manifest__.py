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
    'name': 'Account Analytic Extra Criteria',
    'version': '14.0.0.0.1',
    'summary': 'Account Analytic Extra Criteria',
    'description': """
Account Analytic Extra Criteria
========================================================
Added extra criteria for account analytics
    """,
    'category': 'Accounting',
    'author': 'Vertel AB',
    'website': 'https://www.vertel.se',
    'images': [],
    'depends': ['analytic', 'account', 'account_analytic_move_ids'],
    'data': [
        'views/account_analytic_default_view.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
