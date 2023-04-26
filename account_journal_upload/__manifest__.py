# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Journal Upload Button',
    'version' : '1.1',
    'summary': 'Journal Upload Button',
    'sequence': 10,
    'description': """Added Journal Upload Button""",
    'category': 'Accounting/Accounting',
    'depends' : ['account'],
    'data': [
        'views/account_move_views.xml',
    ],
}
