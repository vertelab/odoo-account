# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Account: Dynamic Reports',
    'version': '18.0.1.0.0',
    'summary': 'Dynamic balance sheet, P&L and general ledger reports for Community Edition.',
    'description': '''
Dynamic Reports
===============

    Dynamic balance sheet, P&L and general ledger reports for Community Edition.

    Features:

        - Web integration: Exposes HTTP endpoints for external systems.
        - Automation: Scheduled jobs: Unrealized Currency Gains/Losses, Balance in Foreign Currency, Balance at Operation Rate.
        - UI Integration: Extends 1 view(s) in the Odoo interface.
        - Extends Odoo: Builds on account.currency.revaluation.report.handler, account.report.
    ''',
    'category': 'Accounting/Reporting',
    'author': 'Vertel Sverige AB',
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
