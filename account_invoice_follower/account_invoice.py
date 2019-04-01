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
        return super(AccountInvoice, self).message_subscribe(partner_ids2, subtype_ids=subtype_ids)
    
    @api.cr_uid_ids_context
    def message_post(self, cr, uid, thread_id, body='', subject=None, type='notification',
                     subtype=None, parent_id=False, attachments=None, context=None,
                     content_subtype='html', **kwargs):
        context = context or {}
        if not context.get('do_not_follow_override'):
            env = api.Environment(cr, uid, context)
            partner_ids = set()
            kwargs_partner_ids = kwargs.pop('partner_ids', [])
            for partner_id in kwargs_partner_ids:
                if isinstance(partner_id, (list, tuple)) and partner_id[0] == 4 and len(partner_id) == 2:
                    partner_ids.add(partner_id[1])
                if isinstance(partner_id, (list, tuple)) and partner_id[0] == 6 and len(partner_id) == 3:
                    partner_ids |= set(partner_id[2])
                elif isinstance(partner_id, (int, long)):
                    partner_ids.add(partner_id)
                else:
                    pass  # we do not manage anything else
            changed = False
            i = 0
            partner_ids2 = set()
            for partner in env['res.partner'].sudo().search_read([('id', 'in', list(partner_ids))], ['do_not_follow']):
                if not partner['do_not_follow']:
                    partner_ids2.add(partner['id'])
            if partner_ids2 != partner_ids:
                context['partner_ids'] = list(partner_ids2)
        return super(AccountInvoice, self).message_post(cr, uid, thread_id, body=body, subject=subject, type=type,
                 subtype=subtype, parent_id=parent_id, attachments=attachments, context=context,
                 content_subtype=content_subtype, **kwargs)

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
        return super(SaleOrder, self).message_subscribe(partner_ids2, subtype_ids=subtype_ids)
    
    @api.cr_uid_ids_context
    def message_post(self, cr, uid, thread_id, body='', subject=None, type='notification',
                     subtype=None, parent_id=False, attachments=None, context=None,
                     content_subtype='html', **kwargs):
        context = context or {}
        if not context.get('do_not_follow_override'):
            env = api.Environment(cr, uid, context)
            partner_ids = set()
            kwargs_partner_ids = kwargs.pop('partner_ids', [])
            for partner_id in kwargs_partner_ids:
                if isinstance(partner_id, (list, tuple)) and partner_id[0] == 4 and len(partner_id) == 2:
                    partner_ids.add(partner_id[1])
                if isinstance(partner_id, (list, tuple)) and partner_id[0] == 6 and len(partner_id) == 3:
                    partner_ids |= set(partner_id[2])
                elif isinstance(partner_id, (int, long)):
                    partner_ids.add(partner_id)
                else:
                    pass  # we do not manage anything else
            changed = False
            i = 0
            partner_ids2 = set()
            for partner in env['res.partner'].sudo().search_read([('id', 'in', list(partner_ids))], ['do_not_follow']):
                if not partner['do_not_follow']:
                    partner_ids2.add(partner['id'])
            if partner_ids2 != partner_ids:
                context['partner_ids'] = list(partner_ids2)
        return super(SaleOrder, self).message_post(cr, uid, thread_id, body=body, subject=subject, type=type,
                 subtype=subtype, parent_id=parent_id, attachments=attachments, context=context,
                 content_subtype=content_subtype, **kwargs)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    do_not_follow = fields.Boolean(string="Do not follow",help="If checked this address will not be added as a follower when invoiced (only for type invoice)")

class EmailTemplate(models.Model):
    _inherit = 'email.template'
    
    do_not_follow_override = fields.Boolean('Ignore Do Not Follow', help="Send this mail even if the recipient has Do Not Follow on.")
    
class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'
    
    @api.multi
    def send_mail(self):
        if self.template_id and self.template_id.do_not_follow_override:
            return super(MailComposeMessage, self.with_context(do_not_follow_override=True)).send_mail()
        return super(MailComposeMessage, self).send_mail()

# ~ class mail_mail(models.Model):
    # ~ _inherit = 'mail.mail'
    
    # ~ @api.model
    # ~ def create(self, values):
        # ~ _logger.warn('\n\nmail.mail.create()\n' + ''.join(traceback.format_stack()) + ('\n\nvalues: %s\n' % values))
        # ~ return super(mail_mail, self).create(values)

# ~ class mail_message(models.Model):
    # ~ _inherit = 'mail.message'
    
    # ~ @api.model
    # ~ def create(self, values):
        # ~ _logger.warn('\n\nmail.message.create()\n' + ''.join(traceback.format_stack()) + ('\n\nvalues: %s\n' % values))
        # ~ return super(mail_message, self).create(values)

# ~ class mail_followers(models.Model):
    # ~ _inherit = 'mail.followers'
    
    # ~ @api.model
    # ~ def create(self, values):
        # ~ _logger.warn('\n\nmail.followers.create()\n' + ''.join(traceback.format_stack()) + ('\n\nvalues: %s\n' % values))
        # ~ return super(mail_followers, self).create(values)

# ~ class mail_thread(models.Model):
    # ~ _inherit = 'mail.thread'
    
    # ~ @api.multi
    # ~ def write(self, values):
        # ~ if 'message_follower_ids' in values:
            # ~ _logger.warn('\n\nmessage_follower_ids: %s\n%s' % (values['message_follower_ids'], ''.join(traceback.format_stack())))
        # ~ return super(SaleOrder, self).write(values)
            # ~ _logger.warn('\n\n' + ''.join(traceback.format_stack()) + ('\n\nmessage_follower_ids: %s\n' % values['message_follower_ids']))
        # ~ return super(mail_thread, self).write(values)
