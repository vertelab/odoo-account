# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2026 Vertel AB (<https://vertel.se>).
#
##############################################################################

{
    'name': 'Account: Payment Date Below Memo',
    'version': '18.0.1.0',
    'summary': 'Move payment_date field below the communication (memo) field',
    'category': 'Accounting',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_payment_register_date',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'description': """
Payment Register Date — View Fix
================================

* Moves the payment_date field below the communication (memo) field
  in the manual payment register wizard.

Note: The default value (invoice due date) is handled by the existing
``payment_date`` module (Linserv). This module only adjusts the view layout.

Related ticket: T/10775
    """,
    'depends': ['account'],
    'data': [
        'views/account_payment_register_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
