{
    'name': 'Account Reconcile Currency Fix',
'author': 'Vertel Sverige AB',
    'version': '1.0',
    'category': 'Accounting',
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
