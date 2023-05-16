{
    'name':'Account Fortnox',
    'description': 'A combination of several modules to bring an invoice integration with fortnox',
    'version':'1.0',
    'author':'Vertel AB',

    'data': [
        'views/res_company_view.xml',
        'views/account_invoice_send_view.xml',
        'views/product_views.xml',
        'data/cron_jobs.xml',

    ],
    'category': 'account',
    'depends': ['crm','membership','l10n_se'],
    'sequence': 5,
    'application': False,
}

