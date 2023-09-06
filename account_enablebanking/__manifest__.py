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
    'name': 'Account: Account Transactions using enable Banking API',
    'version': '14.0.0.0.1',
    'summary': 'Retrieves account transactions using Enable Banking API',
    'category': 'Accounting',
    'sequence': '20',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_enablebanking',
    'images': ['/static/description/banner.png'],  # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'description': """
        Retrieves account transactions using Enable Banking API
    """,
    'depends': ['account', ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter.xml',
        'views/account_journal_view.xml',
        'views/enable_banking_wizard_view.xml',
        'views/res_company_view.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
}


