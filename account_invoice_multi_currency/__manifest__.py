{
    'name': 'Account Invoice multi currency',
    'version': '13.0.1.0',
    'author': 'Kareem Abuzaid, kareem.abuzaid123@gmail.com',
    'website': 'https://kareemabuzaid.com',
    'summery': 'Add all active currencies to the invoice lower table',
    'description': """
        Add all active currencies in the system to the clearfix table
    """,
    'category': 'Accounting/Accounting',
    'depends': [
        'account',
    ],
    'images': ['static/src/img/invoice.png'],
    'data': [
        'views/report_invoice.xml',
        'views/res_config_settings_views.xml',
    ],
    'application': False,
    'installable': True,
}
