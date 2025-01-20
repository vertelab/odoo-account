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
    'name': 'Account: MIS cash flow extend',
    'version': '0.1',
    'summary': '',
    'category': 'Accounting', # Technical Settings|Localization|Payroll Localization|Account Charts|User types|Invoicing|Sales|Human Resources|Operations|Marketing|Manufacturing|Website|Theme|Administration|Appraisals|Sign|Helpdesk|Administration|Extra Rights|Other Extra Rights|
    'description': """
    
    """,
    'sequence': 1,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_mis_cash_flow_extended',
    'images': ['static/description/banner.png'], # 560x280
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'depends': ['account_mis_budget', 'mis_builder','account','mis_builder_budget', 'mis_builder_cash_flow'],
    'data': [
        'security/ir.model.access.csv',
        'data/custom_account_classes.xml',
        'wizard/cash_flow_forecast_wizard.xml',
        'views/mis_cash_flow_forecast.xml',
        'views/mis_cash_flow_forecast_item.xml',
        ],
    'demo': [],
    'application': False,
    'installable': True,    
    'auto_install': False,
}
