# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<https://vertel.se>).
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
    'name': 'Account: Asset Change',
    'version': '1.0',
    'summary': 'Implement Asset changes .',
    'category': 'Accounting',
    'description': """
    Modify or change the asset
    
    * Dispose
    * Sell
    * Modify
    * Pause
    * Move Analytic distribution
    
    """,
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_asset_change',
    'images': ['static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'depends': [
        'account_asset_management'
    ],
    'data': [
	"security/ir.model.access.csv",
    "views/account_asset_views.xml",
    "wizard/account_asset_change_views.xml",
    ],
    "demo": [
    ],
    'installable': True,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
