# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2017 Vertel AB (<http://vertel.se>).
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
    'name' : 'Account Move Line Communtication Payment Order',
    'version' : '1.0',
    'summary':'Sets payment.lines communication field to the name of the account.move as a last resort',
    'description':'This module makes it possible to make account.payment.lines out of account.move.lines whos "res" field is blank.' 
                'The account.payment.lines set their \"communication\" field to account.moves \"res\" field which is a required field and is always blank. When i know what i should fill the account.move res field with then i will change this module' ,
    'category': 'Accounting',
    'author': 'Vertel AB',
    'website': 'http://www.vertel.se',
    'images': [],
    'depends': ['account_payment_order'],
    'data': [
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,

}
