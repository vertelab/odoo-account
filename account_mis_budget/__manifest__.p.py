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
#
# https://www.odoo.com/documentation/14.0/reference/module.html
#
{
    'name': 'Account: MIS Budget',
    'version': '0.1',
    'summary': 'Lets us generate budget based on the previous year.',
    'category': 'Accounting', # Technical Settings|Localization|Payroll Localization|Account Charts|User types|Invoicing|Sales|Human Resources|Operations|Marketing|Manufacturing|Website|Theme|Administration|Appraisals|Sign|Helpdesk|Administration|Extra Rights|Other Extra Rights|
    'description': """
        Lets us generate budget based on the previous year.
        Also lets us add two budgets together into a new one.
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_mis_budget',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'depends': ['date_range', 'account', 'mis_builder_budget', 'mis_builder'],
    'data': [
        "security/ir.model.access.csv",
        "data/custom_account_classes.xml",
        "wizard/make_kpi_report.xml",
        "wizard/make_account_budget.xml",
        "wizard/make_account_forecast.xml",
        "wizard/last_years_actuals.xml",
        "views/mis_budget_by_account.xml",
        "views/kpi_mis_budget_view.xml",
        "views/mis_budget_by_kpi_item.xml",
        "views/mis_budget_by_account_item.xml",
    ],
    'demo': [],
    'application': False,
    'installable': True,    
    'auto_install': False,
}
