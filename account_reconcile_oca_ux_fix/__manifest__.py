{
    'name': 'Account: Reconcile OCA UX Fix',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_reconcile_oca_ux_fix',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Keeps the partner filter in the reconcile tab after manual operation.',
    'description': '''
Reconcile OCA UX Fix
====================

    Fixes a UX issue in the Reconcile tab: the customer filter was reset when
switching to the Manual operation tab and back again.

The fix preserves the selected filter across tab switches.
    ''',
    'depends': ['account_reconcile_oca'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'account_reconcile_oca_ux_fix/static/src/js/reconcile_controller_patch.esm.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
}
