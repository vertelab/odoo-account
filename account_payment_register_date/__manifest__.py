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
    'summary': 'Default payment date to invoice due date, move field below memo',
    'category': 'Accounting',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_payment_register_date',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'description': """
Payment Register Date
=====================

* Defaults the payment_date to the earliest invoice due date when opening
  the manual payment register wizard.
* Moves the payment_date field below the communication (memo) field in the
  form view for better UX.

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
