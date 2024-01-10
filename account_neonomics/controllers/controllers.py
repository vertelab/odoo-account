# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import http
from odoo.http import request
import werkzeug

_logger = logging.getLogger(__name__)

class NeonomicsController(http.Controller):
    _return_url = '/account/neonomics/return'

    @http.route([_return_url], type='http', auth='user', methods=['GET'])
    def neonomics_callback(self, **post):
        wizard_id = request.env["neonomics.wizard"].sudo().create({
            'code': post.get('code'),
        })

        return werkzeug.utils.redirect(
            f'/web#id={wizard_id.id}&model=neonomics.wizard&view_type=form&menu_id='
        )


