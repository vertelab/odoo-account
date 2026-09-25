{
    'name': 'Account: Reconcile Currency Fix',
'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_reconcile_currency_fix',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Fixes currency formatting in the OCA reconciliation widget.',
    'description': '''
Reconcile Currency Fix
======================

    Correct currency formatting for amounts in the OCA reconciliation widget.
    The widget formats debit, credit and currency amounts with the line's own
    currency instead of the company currency.

    Features:

        - Focused Fix: A small, targeted improvement to standard Odoo behaviour.
    ''',
    'depends': ['account_reconcile_oca'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'account_reconcile_currency_fix/static/src/js/reconcile_data_widget_patch.esm.js',
        ],
    },
    'installable': True,
    'license': 'AGPL-3',
}
