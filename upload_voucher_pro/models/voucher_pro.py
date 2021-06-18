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


class account_voucher(models.Model):
    _inherit = 'account.voucher'

    account_type = fields.Selection(selection = [('5400', 'Förbrukningsmateriel'), ('7699', 'Personal / fika')])
    description = fields.Char(string='Notering', size=64, trim=True, )


class upload_voucher_pro(http.Controller):

    # ~ @http.route(['/file/<model("ir.attachment"):file>',], type='http', auth='user')
    @http.route('/upload_voucher_pro', type='http', auth='public', website=True)
    def upload_attachement(self, account=False, **post):
        message = {}
        voucher = []

        # ~ and post.get('ufile')
        # ~ 'partner_id': 1084,
        # ~ 'account_voucher': 12
        
        # ~ def voucher_in(self,):
        # ~ vouchers = []
        # ~ for issue in self:
            # ~ record = self.env['account.voucher'].with_context({'default_type': 'purchase', 'type': 'purchase'}).default_get(['journal_id','date','period_id'])
            # ~ record.update({
                # ~ 'voucher_type': 'purchase',
                # ~ 'account_id': issue.partner_id.property_account_receivable_id.id,
                # ~ 'name': issue.description,
                # ~ 'reference': issue.name,
            # ~ })
            # ~ voucher = self.env['account.voucher'].create(record)
            # ~ issue._finnish(voucher,_('Supplier voucher created'))
            # ~ vouchers.append(voucher)
        # ~ return self._get_views(voucher,'account_voucher.action_purchase_receipt', form='account_voucher.view_purchase_receipt_form')
        
        _logger.warning('NILS: %s' % request.httprequest.method)
        if request.httprequest.method == 'POST':
            _logger.warning('NILS: Got here 1')
            # ~ _logger.warning('NILS: voucher_type : %s' % post.get('voucher_type') )
            # ~ _logger.warning('NILS: voucher_type : %s' % type(post.get('voucher_type')) )
            # ~ _logger.warning('NILS: voucher_type : %s' % type(int(post.get('voucher_type'))) )
            # ~ _logger.warning('NILS: account_type : %s' % post.get('account_type') )
            # ~ _logger.warning('NILS: account_type : %s' % type(post.get('account_type')) )

            vals = request.env['account.voucher'].with_context({
                'default_voucher_type': 'purchase',
                'voucher_type': 'purchase',
                'default_pay_now': 'pay_now',
                'pay_now': 'pay_now'}).default_get(['journal_id', 'date',
                    'currency_id', 'company_id','period_id', 'pay_now', 'payment_journal_id'])
            _logger.warning('NILS vals = %s' %  vals)
            account = request.env['account.journal'].browse(12).default_debit_account_id
            vals['account_id'] = account.id
            partner_id = request.env['res.partner'].search([('id', '=', 1084)], limit=1)
            _logger.warning('NILS: Got here 2 %s' % partner_id)
            if partner_id:
                vals.update({'partner_id': partner_id.id })
                
            voucher = request.env['account.voucher'].create(vals)
            _logger.warning('NILS %s' %  voucher)
            account = request.env['account.account'].search([('code', '=', post.get('account_type') )], limit=1)
            
            for vat, vat_id in (('vat6', 'I6'), ('vat12','I12'), ('vat25','I')):
                if not post.get(vat):
                    continue
                vat_obj = request.env['account.tax'].search([('name', '=', vat_id)], limit=1)
                line = request.env['account.voucher.line'].create({
                    'voucher_id': voucher.id,
                     'name': account.name,
                     'account_id': account.id,
                     'quantity': 1.0,
                     'price_unit': post.get(vat),
                     'tax_ids': [(6, 0, [vat_obj.id])]
                     })

            _logger.warning('NILS: Got here 3')
    

            message['success'] = _('Voucher uploaded %s (%s)') % (voucher.id if voucher else None, account.id if account else None)
        else:
            message['success'] = _('Voucher uploaded %s (%s)') % (account.id if account else None, account.id if account else None)
 
        _logger.warning('<<<<< 2. VALUES: user = render!!')
        return request.render('upload_voucher_pro.upload_attachement_pro', {'message': message,
                                                     # ~ 'res_company': request.env['res.company'].browse(1),
                                                     'partner_id': 1,
                                                     'account_type': '5400',
                                                     'vat6': '6',
                                                     'vat12': '12',
                                                     'vat25': '25',
                                                     'description': 'description',
                                                     # ~ 'website': request.env['res.company'].browse(1),
                                                     })


    # ~ if condition TRUE:
          # ~ return request.render(module_name.templateID1')  or request.redirect('/')
    # ~ else:
         # ~ return request.render('web.login', values)


    def upload_attachement_pro(self, account=False, **post):
        message = {}
        user = request.env['res.users'].browse(request.env.user.id)
        voucher_name = None

        _logger.warning('<<<<< 3. VALUES: user = hello world!!')
        account = request.env['project.account'].create({'partner_id': user.partner_id.id,
                                                     'pay_now' : 'pay_now',
                                                     # ~ 'payment_journal_id' : post.get(''),
                                                     'journal_id' : post.get(''),
                                                     'account_type': post.get('account_type'),
                                                     'vat6': post.get('vat6'),
                                                     'vat12': post.get('vat12'),
                                                     'vat25': post.get('vat25'),
                                                     'description': post.get('description'),
                                                     'project_id': project[0].id if len(project) > 0 else None,
                                                     'voucher_type': post.get('voucher_type'),
                                                     })

        _logger.warning('<<<<< 4. VALUES: user = hello world!!')
        if request.httprequest.method == 'POST':
            message['success'] = _('Voucher uploaded %s (%s)') % (account.name,issue.id)

        _logger.warning('<<<<< 5. VALUES: user = hello world!!')
        if request.httprequest.method == 'POST' and post.get('ufile'):
            message['success'] = _('Voucher uploaded %s (%s)') % (account.name,issue.id)

        _logger.warning('<<<<< 6. VALUES: user = hello world!!')

        _logger.error("('<<<<<  This is a %s and %s and %s, %s" % (type(account),isinstance(account,models.Model),account,request.httprequest.url))
        # ~ _logger.error("('<<<<<  This is a %s and %s and %s, %s" % (type(issue),isinstance(issue,models.Model),issue,request.httprequest.url))
        return request.render("upload_voucher_pro.upload_attachement_pro", {
                # ~ 'issue': False if re.search("upload_voucher",request.httprequest.url) is not None else issue,
                'message': message,
                # ~ 'attachements': account and request.env['ir.attachment'].search([('res_model','=','project.account'),('res_id','=',account.id)]) or False,
            })


        @http.route(['/file/<model("ir.attachment"):file>',], type='http', auth='user')
        def file_download(self, file=False, **kw):
            return request.make_response(base64.b64decode(file.datas),
                    [('Content-Type', file.mimetype),
                     ('Content-Disposition', content_disposition(file.name))])

def content_disposition(filename):
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
