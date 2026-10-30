# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel Sverige AB (<https://vertel.se>).
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
    'name': 'Account: Accounting UI (CE)',
    'version': '18.0.1.2.4',
    # Version ledger: 18.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Community accounting UI adjustments: "Accounting" naming and two form fields.',
    'category': 'Accounting',
    'description': '''
Accounting UI (CE)
==================

    UI adjustments that make Community accounting read as "Accounting"
    instead of "Invoicing", plus two fields that Community only shows in
    list views.

    What this module does:

        - Renames the accounting app category from "Invoicing" to
          "Accounting" (Apps list and user form).
        - Renames the top-level menu from "Invoicing" to "Accounting".
        - Renames the settings app title from "Invoicing" to "Accounting".
        - Keeps the account sub-menus (Dashboard, Customers, Vendors,
          Accounting, Assets, Reporting, Configuration) as children of that
          root, so the UI shows one accounting app and not seven roots.
        - Shows "Allow Reconciliation" (`reconcile`) on the account form.
        - Shows the inalterability hash (`inalterable_hash`) on journal
          entries for developers (`base.group_no_one`).
        - Restricts the partner accounting entries group to
          `account.group_account_basic`.

    What this module does NOT do:

        - It owns no models and adds no business logic; it is a pure UI
          module. Fiscal year management lives in `account_fiscal_year_vrtl`.
        - It does not redefine any `account` group. Community's group
          architecture (`account/security/account_security.xml`) is left
          untouched.

    Dependencies:

        account_asset_management
                https://github.com/OCA/account-financial-tools
    ''',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_accountant_ce',
    'images': ['static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'depends': [
        # `menu_finance_assets` is reparented in data/account_asset_menu.xml,
        # so the module that owns that menu must be loaded first.
        'account_asset_management',
    ],
    'data': [
        'security/account_accountant_security.xml',
        'data/account_accountant_data.xml',
        'data/account_asset_menu.xml',
        'views/account_move_views.xml',
        'views/account_account_views.xml',
        'views/product_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
}
