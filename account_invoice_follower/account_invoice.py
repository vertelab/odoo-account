# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2018 Vertel AB (<http://vertel.se>).
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

from openerp import api, models, fields, _
import logging
_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    @api.multi
    def message_subscribe(self, partner_ids, subtype_ids=None):
        partner_ids2 = []
        for partner in self.env['res.partner'].sudo().search_read([('id', 'in', partner_ids)], ['do_not_follow']):
            if not partner['do_not_follow']:
                partner_ids2.append(partner['id'])
        if not partner_ids2:
            return True # or False?
        return super(AccountInvoice, self).message_subscribe(partner_ids, subtype_ids=None)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    @api.multi
    def message_subscribe(self, partner_ids, subtype_ids=None):
        partner_ids2 = []
        for partner in self.env['res.partner'].sudo().search_read([('id', 'in', partner_ids)], ['do_not_follow']):
            if not partner['do_not_follow']:
                partner_ids2.append(partner['id'])
        if not partner_ids2:
            return True # or False?
        return super(SaleOrder, self).message_subscribe(partner_ids, subtype_ids=None)

class res_partner(models.Model):
    _inherit = 'res.partner'

    do_not_follow = fields.Boolean(string="Do not follow",help="If checked this address will not be added as a follower when invoiced (only for type invoice)")
