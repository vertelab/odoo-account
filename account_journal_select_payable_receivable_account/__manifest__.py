# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2021- Vertel AB (<https://vertel.se>).
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
    'name': 'Account: Journal Select Payable Receivable Account',
    'version': '14.0.0.0.1',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Adds two new fields on a journal so that we can control which Payable Receivable Account odoo uses when it balances an Invoice/Journal Entry',
    'category': 'Accounting',
    #'sequence': '1',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-account/account_journal_select_payable_receivable_account',
    'images': ['static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'description': """
	Adds two new fields on a journal so that we can control which Payable Receivable Account odoo uses when it balances an Invoice/Journal Entry.
	Odoo uses the first payable/receivable account it can find using the search method, so if you have more than one you can't control which one is used.

	Payable are used on on everything except Customer Invoice, Customer Credit Note, Sales Receipt.
	Receivable are used on Customer Invoice, Customer Credit Note, Sales Receipt.
	
    """,
    'depends': ['account'],
    'data': [
        'views/journal_view.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
