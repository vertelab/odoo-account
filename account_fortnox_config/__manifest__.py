# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Membership Invoice FortNox Conf',
    'version': '1.0',
    'category': 'memberhsip',
    'author':'Vertel AB',
    'description': """
This module extends the invoicing capabilities for membership-module
    """,
    'depends': ['account'],
    'data': [
        
        
        'views/res_config_settings_views.xml',
        
        'data/ir_actions_server.xml',
        
    ],
    'website': 'vertel.se',
}
