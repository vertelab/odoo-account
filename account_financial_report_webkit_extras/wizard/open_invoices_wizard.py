# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright Camptocamp SA 2012
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
from openerp import models, fields


class AccountReportOpenInvoicesWizard(models.TransientModel):
    """Will launch Open Invoices report and pass required args"""
    _inherit = "open.invoices.webkit"
    
    accounts_ids = fields.Many2many(
        comodel_name='account.account', string='Filter on account',
        help="Only selected accounts will be printed. Leave empty to print "
        "all accounts."
    )

    # pylint: disable=old-api7-method-defined
    def pre_print_report(self, cr, uid, ids, data, context=None):
        data = super(AccountReportOpenInvoicesWizard, self).pre_print_report(
            cr, uid, ids, data, context=context)
        vals = self.read(cr, uid, ids,
                         ['accounts_ids'],
                         context=context)[0]
        data['form'].update(vals)
        return data
