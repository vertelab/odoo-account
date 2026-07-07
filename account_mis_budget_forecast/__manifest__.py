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
    'name': 'Account: MIS Budget Forecast & Hierarchy',
    'version': '18.0.1.0.0',
    'summary': 'Dynamic forecast replacing budget with actuals, and hierarchical budget trees.',
    'category': 'Accounting',
    'author': 'Vertel AB',
    'website': 'https://vertel.se',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'description': """
Adds two features to MIS Budget:

1. Dynamic Forecast
   A budget marked as forecast automatically replaces budget amounts with
   actual booked figures for elapsed periods, while keeping budget figures
   for future periods. Inspired by Fortnox Rapport & Analys.

2. Hierarchical Budget Trees
   Configure budget trees with nodes and leaves. Nodes auto-sum their
   children. Leaves map to accounts via account-code masks.
   Inspired by Visma.net ERP budget tree.
    """,
    'depends': ['account_mis_budget', 'mis_builder_budget', 'date_range', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/mis_budget_forecast_views.xml',
        'views/mis_budget_tree_views.xml',
        'views/mis_budget_item_views.xml',
        'wizard/make_forecast_wizard.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
