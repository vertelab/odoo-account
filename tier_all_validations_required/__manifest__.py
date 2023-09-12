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
    'name': 'Account: Tier All Validations Required',
    'version': '14.0.0.1.0',
    'summary': '',
    'category': 'Accounting',
    'description': """
    """,
    #'sequence': 1,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/tier_all_validations_required/',
    'license': 'AGPL-3',
    'depends': ['base_tier_validation', 'account_move_tier_validation', 'account_move_tier_validation_implement'],
    'data': [
        'views/tier_definition_view.xml',
        'views/tier_review_view.xml',
        'views/account_move_view.xml',
    ],
    'demo': [],
    'application': False,
    'installable': True,    
    'auto_install': False,
    "qweb": ["static/src/xml/tier_review_template.xml"],
    #"post_init_hook": "post_init_hook",
}
