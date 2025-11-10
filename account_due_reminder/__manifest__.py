# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<https://vertel.se>).
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
    'name': 'Account: Invoice Payment Reminder',
    'version': '1.0',
    'summary': 'Invoice Payment Reminder',
    'category': 'Accounting',
    'description': """
        Invoice Payment Reminder
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_due_reminder',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/payment_reminder_line_views.xml',
        'views/account_payment_terms_views.xml',
        'views/account_move_views.xml',
        'data/account_followup_data.xml',
        'data/cron.xml',
    ],
    'installable': 'True',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
