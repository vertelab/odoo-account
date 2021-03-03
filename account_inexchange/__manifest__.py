{
    'name':'Inexchange Invoice',
    'description': 'Fields for invoicing through Inexchange',
    'version':'1.0',
    'author':'Vertel AB',

    'data': [
        'views/res_config_settings_view.xml',
        'views/res_company_view.xml',
        'views/account_invoice_send_view.xml',
    ],
    'category': 'account',
    'depends': ['l10n_se','sale'],
    'sequence': 5,
    'application': False,
}

