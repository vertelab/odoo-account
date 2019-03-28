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

class mail_followers(models.Model):
    _inherit = 'mail.followers'
    
    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, values):
        if values.get('res_model') in ('sale.order', 'account.invoice'):
            if self.env['res.partner'].search_read([('id', '=', values['partner_id'])], ['do_not_follow'])[0]['do_not_follow']:
                return self.browse()
        return super(mail_followers, self).create(values)

class res_partner(models.Model):
    _inherit = 'res.partner'

    do_not_follow = fields.Boolean(string="Do not follow",help="If checked this address will not be added as a follower when invoiced (only for type invoice)")
