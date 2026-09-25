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
    'name': 'Account: Invoice AI Mailbox',
    'version': '18.0.1.0.3',
    'summary': 'Adds a mailbox for AI-assisted invoice handling.',
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'account',
    'description': '''
Invoice AI Mailbox
==================

    Adds a mailbox for AI-assisted invoice handling.

    Features:

        - Automation: Scheduled jobs: Mail Analyst, Analyse incoming invoices, Supervisor for Analyse incoming invoices.
        - Guided Wizards: Step-by-step dialogs for data entry.
        - UI Integration: Extends 5 view(s) in the Odoo interface.
        - Extends Odoo: Builds on account.journal, account.move, ai.agent, ai.quest.
    ''',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_invoice_ai',
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'depends': [
        'ai_agent',
        'account',
        'account_period_vrtl',
        'account_invoice_import',
        'purchase'
    ],
    'data': [
        'data/ai_tool_data.xml',
        'data/ai_invoice_mail.xml',
        'data/ai_invoice_attachment.xml',
        'views/ir_attachment_view.xml',
        'views/account_move_view.xml',
        'views/res_partner_view.xml',
        'views/ai_quest_session_views.xml',
        'views/ai_agent_view.xml',
    ],
    'external_dependencies': {
        'python': [
            'eml_parser',
            #"pyarrow",
            'pytesseract', 
            'PyMuPDF',
            #"faiss-cpu",
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}