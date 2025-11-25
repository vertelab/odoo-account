# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2025- Vertel AB (<https://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Account: Move Directory',
    'version': '1.0',
    'summary': 'Loads moves from a directory and store them on a account move.',
    'category': 'Accounting',
    'description': """
    Account Move Directory
    ============================
    Loads moves from a directory and store them on a account move. 
    The filename is important for finding the correct Account Move and nameing the file as an move. Use the form <Account Move Name>_<filename.extension>.
    Use dash (-) instead of '/'. Example LEV-2025-11-004_MyFile.pdf will be an move on Account move LEV/2025/11/0004 and have the name MyFile.pdf

    service account_move_direcory [start,stop,status]
    You have to restart the service when the dairectory is changed

    Look for errors in the error-directory and the log

    """,
    #'sequence': '1'
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_move_directory',
    'images': ['static/description/banner.png'], # 560x280 px
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'depends': ['account', 'edi_base'],
    'data': [
        'data/message_formart.xml',
        'views/res_config_settings_views.xml',
        'views/edi_message_views.xml',

        # 'security/ir_rule.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
