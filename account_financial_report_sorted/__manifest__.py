# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2025- Vertel AB (<https://vertel.se>).
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
    'name': 'Account Financial Report Sorted',
    'version': '1.1.0',
    'summary': 'Fixes sorting and UX for Aged Partner Balance report',
    'category': 'account',
    'description': """
        Extends OCA account_financial_report with:
        - Alphabetically sorted partners in Aged Partner Balance
        - Clickable partner names to view underlying invoices
        - Back-to-wizard button for filter changes
    """,
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_financial_report_sorted',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'depends': [
        'account_financial_report',
    ],
    'data': [
        'report/templates/aged_partner_balance.xml',
        'wizard/aged_partner_balance_wizard_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_financial_report_sorted/static/src/js/aged_partner_sort.esm.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
