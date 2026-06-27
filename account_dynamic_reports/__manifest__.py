# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Accounting: Dynamic Reports',
    'version': '18.0.1.0.0',
    'summary': 'Dynamic accounting reports for Odoo CE — balance sheet, P&L, general ledger, and more',
    'category': 'Accounting/Reporting',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_dynamic_reports',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/balance_sheet.xml',
        'data/report_actions.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'account_dynamic_reports/static/src/components/account_report/*.js',
            'account_dynamic_reports/static/src/components/account_report/*.xml',
            'account_dynamic_reports/static/src/scss/account_report.scss',
        ],
    },
    'installable': True,
    'application': False,
}
