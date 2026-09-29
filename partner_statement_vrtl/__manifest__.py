# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2026- Vertel AB (<https://vertel.se>).
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Partner Statement (Vertel)',
    'version': '18.0.1.0.0',
    'summary': 'Consistent sign convention and remaining amount for partner statements',
    'category': 'Accounting/Accounting',
    'description': """
Extends OCA partner_statement with a consistent sign convention and an
explicit remaining amount.

Features:

* Amounts owed by the customer are positive, credit balances (credit
  notes, unapplied prepayments) are negative.
* An explicit Reconciled column (original minus remaining).
* An explicit Remaining column computed from reconciliations.

Background (T/11336): prepayments that have been reconciled against
invoices disappear from the OCA open-items reports, and the remaining
prepayment amount is not visible. See the task description for the full
investigation.
    """,
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/partner_statement_vrtl',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'depends': [
        'partner_statement',
    ],
    'data': [
        'views/outstanding_statement.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
