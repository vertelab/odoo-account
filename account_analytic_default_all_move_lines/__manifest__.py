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
    'name': 'Account: Default Analytic Move Line Ids',
    'version': '14.0.0.0.1',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': '',
    'category': 'Accounting',
    'description': "Analytic Default rules aren't applied on line ids on a account move, so typically tax lines that odoo generates which aren't in the invoice line tab. This module changes that, now Analytic Default rules are applied to these kinds of lines as well",
    #'sequence': '1'
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account-analytic-default-all-move_lines',
    'images': ['static/description/banner.png'], # 560x280 px
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'description': """
Account Analytic Move Default Rules
========================================================
Changes the behaviour of account analaytic default rules
Analytic Default rules aren't applied on line ids on a account move, so typically tax lines that odoo generates which aren't in the invoice line tab. This module changes that, now Analytic Default rules are applied to these kinds of lines as well
Have also changed it so that analytic tags aren't removed when calulating analaytic default rules. So it just keeps adding.

    """,
    'depends': ['analytic', 'account'],
    'data': [
        # ~ 'views/account_move_views.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
