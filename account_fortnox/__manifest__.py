# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2023- Vertel Sverige AB (<https://vertel.se>).
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
    'name': 'Account: Odoo - Fortnox Integration',
    'version': '18.0.1.0.0',
    # Version ledger: XX.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Syncs invoices and payments with Fortnox.',
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'description': '''
Odoo - Fortnox Integration
==========================

    The module connects Odoo with the Fortnox accounting platform. It exports
        invoices and payment information and keeps the two systems in sync through
        scheduled jobs and API endpoints.

    Features:

        - Web integration: Exposes HTTP endpoints for external systems.
        - Automation: Scheduled jobs: Fortnox Invoice Status.
        - UI Integration: Extends 7 view(s) in the Odoo interface.
        - Extends Odoo: Builds on account.fiscal.position, account.incoterms, account.journal, account.move.
    ''',
    #'sequence': '1',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_fortnox',
    'images': ['static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    # Any module necessary for this one to work correctly

    'depends': ['crm', 'membership', 'l10n_se', 'sale_management'],
    'data': [
        'views/res_company_view.xml',
        'views/account_invoice_send_view.xml',
        'views/product_views.xml',
        'views/account_journal.xml',
        'views/res_partner_view.xml',
        'views/account_payment_term_view.xml',
        'views/account_incoterm_view.xml',
        'data/cron_jobs.xml',

    ],
    'sequence': 5,
    'application': False,
}
