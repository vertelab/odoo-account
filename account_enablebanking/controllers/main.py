# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import http
from odoo.http import request
import werkzeug
import json

_logger = logging.getLogger(__name__)


class EnableBankingController(http.Controller):
    _return_url = '/account/enable-banking/return'

    @http.route([_return_url], type='http', auth='user', methods=['GET'])
    def enable_banking_callback(self, **post):
        wizard_id = request.env["enable.banking.wizard"].sudo().create({
            'code': post.get('code'),
        })

        return werkzeug.utils.redirect(
            f'/web#id={wizard_id.id}&model=enable.banking.wizard&view_type=form&menu_id='
        )


