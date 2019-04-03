# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2019 Vertel AB (<http://vertel.se>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
'name': 'Account Invoice Round',
'version': '0.1',
'summary': 'Rounds invoices and creates moves according to.',
'category': 'account',
'description': """This modules adds the ability to round the total amount on customer invoices to nearest amount without cents. 
It's possible to turn off this feature on any single invoice using a checkbox near the rounding amount on the invoice form.

The created Entry and payment order are corrected with the new amount. The difference between total amount and rounded total amount
are posted on a rounding account. 

The account used for rounding are a system parameter 'account_invoice_round.account_round' and defaults to 3740
(swedish basplanen).""",
'author': 'Vertel AB',
'license': 'AGPL-3',
'website': 'http://www.vertel.se',
'depends': ['account',],
'data': ['account_invoice_view.xml'], 
'installable': True,
}
