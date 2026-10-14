# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
#
##############################################################################

{
    'name': 'Account: Payment Date Below Memo',
    'version': '18.0.1.0.0',
    'summary': 'Defaults the payment date to the invoice due date.',
    'category': 'Accounting',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_payment_register_date',
    'license': 'AGPL-3',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'description': '''
Payment Date Below Memo
=======================

    Defaults the payment date to the invoice due date.

    Features:

        - Guided Wizards: Step-by-step dialogs for data entry.
        - UI Integration: Extends 1 view(s) in the Odoo interface.
    ''',
    'depends': ['account'],
    'data': [
        'views/account_payment_register_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
