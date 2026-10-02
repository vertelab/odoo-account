# Copyright 2026 Vertel AB
# SPDX-License-Identifier: AGPL-3
{
    'name': 'Account: Vendor Bill Approval Migration',
    'version': '18.0.1.1.0',
    'category': 'Accounting',
    'summary': 'Migrates data from purchase_vendor_bill_approval to the new approval module.',
    'description': '''
Vendor Bill Approval Migration
==============================

    Migrates data from purchase_vendor_bill_approval to the new approval module.

    Features:

        - Focused Fix: A small, targeted improvement to standard Odoo behaviour.
    ''',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_bill_approval_migration',
    'license': 'AGPL-3',
    'depends': [
        'account_bill_approval',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'application': False,
}
