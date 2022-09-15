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
    'name': 'Account move validation implement control',
    'version': '14.0.0.0.0',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': '',
    'category': 'Accounting',
    'description': '',
    #'sequence': '1'
    'author': 'Vertel AB',
    # ~ 'website': 'https://vertel.se/apps/odoo-account/account-analytic-move-ids',
    # ~ 'images': ['/static/description/banner.png'], # 560x280 px
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'description': """
        Adds two new fields on a user. 
        1. Is a field to set if they are supposed to show up in the validation fields on an invoice.
        2. Is how much is that person allowed to validate.
    """,
    'depends': ['account_move_tier_validation_implement', 'base'],
    'data': [
        'views/res_users_views.xml',
        'views/account_move_views.xml',
        # 'data/validator_group.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
