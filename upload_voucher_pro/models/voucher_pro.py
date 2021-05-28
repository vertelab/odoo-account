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
#    2021-05-27 CODE FROM: odoo-account-extra/website_project_issue/models/project_issue.py
#
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import except_orm, Warning, RedirectWarning
from odoo import http
from odoo.http import request
from odoo import SUPERUSER_ID
from datetime import datetime
import werkzeug
import pytz
import base64
from odoo.tools import ustr
import urllib2
import re
import time

from wand.image import Image
from wand.display import display
from wand.color import Color
import subprocess


import logging
_logger = logging.getLogger(__name__)


def content_disposition_pro(filename):
    filename = ustr(filename)
    escaped = urllib2.quote(filename.encode('utf8'))
    browser = request.httprequest.user_agent.browser
    version = int((request.httprequest.user_agent.version or '0').split('.')[0])
    if browser == 'msie' and version < 9:
        return "attachment; filename=%s" % escaped
    elif browser == 'safari':
        return u"attachment; filename=%s" % filename
    else:
        return "attachment; filename*=UTF-8''%s" % escaped

class account_voucher(models.Model):
    _inherit = 'account.voucher'
    _logger.warning('<<<<< 1. VALUES: user = hello world!!')

    account_type = fields.Selection(selection = [('5400', 'Förbrukningsmateriel'), ('7699', 'Personal / fika')])
    description = fields.Char(string='Notering', size=64, trim=True, )

class upload_voucher_pro(http.Controller):
    _logger.warning('<<<<< 2. VALUES: user = hello world!!')

    @http.route(['/project/issue/<model("project.issue"):issue>/attachment_pro','/project/issue/new/attachment_pro', '/upload_voucher_pro'], type='http', auth="user", website=True)
    def upload_attachement_pro(self, issue=False, **post):
        message = {}
        user = request.env['res.users'].browse(request.env.user.id)
        voucher_name = None

        _logger.warning('<<<<< 3. VALUES: user = hello world!!')
        if request.httprequest.method == 'POST':
            _logger.warning('<<<<< 33. VALUES: user = hello world!!')
            try:
                voucher_name = [txt[1] for txt in request.env['project.issue'].fields_get(['voucher_pro_type'])['voucher_pro_type']['selection'] if txt[0] == post.get('voucher_pro_type')][0]
                project = request.env['project.project'].search(['&',('partner_id','=',user.partner_id.id),('use_voucher','=',True)])
                issue = request.env['project.issue'].create({'partner_id': user.partner_id.id,
                                                             'name': '%s %s' % (voucher_name,post.get('name','')),
                                                             'description': post.get('description'),
                                                             'project_id': project[0].id if len(project) > 0 else None,
                                                             'voucher_type': post.get('voucher_type'),
                                                             })
            except Exception as e:
                message['danger'] = _('Could not create an issue %s') % e

        _logger.warning('<<<<< 4. VALUES: user = hello world!!')
        if request.httprequest.method == 'POST':
            _logger.warning('<<<<< 44. VALUES: user = hello world!!')
            issue.write({'partner_id': user.partner_id.id, 'name':  '%s %s' % (voucher_name,post.get('name','')), 'description': post.get('description')})

        _logger.warning('<<<<< 5. VALUES: user = hello world!!')
        if request.httprequest.method == 'POST' and post.get('ufile'):
            _logger.warning('<<<<< 55. VALUES: user = hello world!!')
            _logger.debug("This is attachement post %s /issue/nn" % (post))
            blob = post['ufile'].read()
            attachment = request.env['ir.attachment'].with_context({'convert': 'pdf2image'}).create({
                    'name': post['ufile'].filename,
                    'res_name': issue.name,
                    'res_model': 'project.issue',
                    'res_id': issue.id,
                    'datas': base64.encodestring(blob),
                    'datas_fname': post['ufile'].filename,
                })
            if attachment.mimetype == 'application/pdf':
                attachment.pdf2image(800,1200)
            elif attachment.mimetype in ['image/jpeg','image/png','image/gif']:
                orientation = {
                    'top_left': 0,
                    'left_top': 0,
                    'right_top': 90,
                    'top_right': 90,
                    'right_bottom': 180,
                    'bottom_right': 180,
                    'left_bottom': 270,
                    'bottom_left': 270,
                }
                try:
                    img = Image(blob=blob)
                    img.rotate(orientation.get(img.orientation))
                    attachment.datas = base64.encodestring(img.make_blob(format='jpg'))
                except:
                    pass
            message['success'] = _('Voucher uploaded %s (%s)') % (issue.name,issue.id)

        _logger.warning('<<<<< 6. VALUES: user = hello world!!')

        _logger.error("This is a %s and %s and %s, %s" % (type(issue),isinstance(issue,models.Model),issue,request.httprequest.url))
        return request.render("upload_voucher_pro.upload_attachement_pro", {
                'message': message,
            })


    @http.route(['/file/<model("ir.attachment"):file>',], type='http', auth='user')
    def file_download(self, file=False, **kw):
        return request.make_response(base64.b64decode(file.datas),
                [('Content-Type', file.mimetype),
                 ('Content-Disposition', content_disposition(file.name))])

