# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2022- Vertel AB (<https://vertel.se>).
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
    'name': 'Account: Split Invoice by Attachments',
    'version': '14.0.0.1.0',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Split an invoice with many attachments into copies with single files',
    'category': 'Accounting',
    'description': """
    Adds an "Split Invoice from Attachments" option to the action menu of invoices.
    The action takes the current open invoice and creates a copy of it for each file attached to the original. The original invoice is then removed.
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_admin_rights',
    #'images': ['static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'depends': ['account','mail'],
    'data': [
        'views/account_move.xml',
    ],
    'installable': 'True',
}
