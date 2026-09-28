{
    'name': 'Account: Reconcile OCA UX Fix',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_reconcile_oca_ux_fix',
    'version': '18.0.1.1.0',
    'category': 'Accounting',
    'summary': 'Keeps the search filter in the reconcile tab after manual operation.',
    'description': '''
Reconcile OCA UX Fix
====================

    Fixes a UX issue in the Reconcile tab: the search filter was reset when
switching to the Manual operation tab and back again.

The cause is that the selected record changes on the tab switch. The newly
selected record belongs to another partner, and its form view installs a new
`search_default_partner_id` filter, which replaces the filter the user set.

The fix keeps the currently selected record when the controller re-selects
after a form reload, so the record does not change and the filter survives.
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
