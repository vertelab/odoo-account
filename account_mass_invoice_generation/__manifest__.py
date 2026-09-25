# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2024- Vertel AB, info@vertel.se
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
    'name': 'Account: Mass Invoice Generation',
    'version': '18.0.1.0.0',
    'summary': 'Generates invoices in bulk for multiple partners.',
    'category': 'Accounting',
    'description': '''
Mass Invoice Generation
=======================

    Module to select an invoice and create bulk invoices for different partners

    Features:

        - UI Integration: Extends 1 view(s) in the Odoo interface.
        - Extends Odoo: Builds on account.move, bulk.account.move.wizard.
    ''',
    #'sequence': 1,
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_mass_invoice_generation',
    'images': ['static/description/banner.png'], # 560x280
    'repository': 'https://github.com/vertelab/odoo-account',
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [
        'views/bulk_account_move_wizard_views.xml',
        'data/ir_actions_server.xml',
        'security/ir.model.access.csv'
    ],
    'demo': [],
    'application': False,
    'installable': True,
    'auto_install': False,
}
