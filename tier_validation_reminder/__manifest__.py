# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) {year} {company} (<{mail}>)
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
#
# https://www.odoo.com/documentation/14.0/reference/module.html
#
{
    'name': 'Account: Tier Validation Reminder',
    'version': '18.0.0.2.0',
    'summary': 'Sends reminder to the next person pending a tier review.',
    'category': 'Accounting',
    'description': """
    Sends reminder to the next person pending a tier review.
    """,
    #'sequence': 1,
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/tier_validation_reminder/',
    'license': 'AGPL-3',
    'repository': 'https://github.com/vertelab/odoo-account',
    'depends': ['base_tier_validation'],
    'data': [
        'data/ir_cron.xml',
        'data/mail.xml',
    ],
    'application': False,
    # INTE INSTALLERBAR: data/ir_cron.xml refererar base_tier_validation_report.model_tier_review.
    # base_tier_validation_report finns inte i något addons-repo på maskinen.
    # Modulen flyttades från odoo-fortnox 2026-11-10 för att inte tappa koden;
    # den kan aktiveras först när beroendet finns.
    'installable': False,
    'auto_install': False,
    #"post_init_hook": "post_init_hook",
}
