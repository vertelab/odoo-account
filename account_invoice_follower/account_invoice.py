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


class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    @api.multi
    def invoice_validate(self):
        followers = self.message_follower_ids.filtered(lambda f: not f.do_not_follow)
        self.message_follower_ids = followers
        _logger.warn('Invoice_validate Do not follow %s ' %self.message_follower_ids)
        return super(account_invoice, self).invoice_validate()
        
    # ~ @api.multi
    # ~ def action_move_create(self):
        # ~ _logger.warn('Action_move_create Do not follow %s ' %self.message_follower_ids)
        # ~ return super(account_invoice, self).action_move_create()
        
    # ~ @api.multi
    # ~ def action_number(self):
        # ~ _logger.warn('Action_number Do not follow %s ' %self.message_follower_ids)
        # ~ return super(account_invoice, self).action_number()

    # ~ @api.multi
    # ~ def action_date_assign(self):
        # ~ _logger.warn('Action_date_assign Do not follow %s ' %self.message_follower_ids)
        # ~ return super(account_invoice, self).action_date_assign()

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    do_not_follow = fields.Boolean(string="Do not follow",help="If checked this address will not be added as a follower when invoice")

class mail_compose_message(models.Model):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self):
        context = self._context
        if context.get('default_model') == 'account.invoice' and \
                context.get('default_res_id') and context.get('mark_invoice_as_sent'):
            invoice = self.env['account.invoice'].browse(context['default_res_id'])
            if invoice.address_invoice_id.do_not_follow:
                invoice = invoice.with_context(mail_post_autofollow=False)
            else:
                invoice = invoice.with_context(mail_post_autofollow=True)
            invoice.write({'sent': True})
            invoice.message_post(body=_("Invoice sent 2"))
            _logger.warn('Do not follow %s ' %invoice)
            return self.send_mail() # Override account.invoice send_mail (sequence low)
        return super(mail_compose_message, self).send_mail()
