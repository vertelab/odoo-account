# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import http
from odoo.http import request
import werkzeug, uuid

_logger = logging.getLogger(__name__)


class SaltedgeController(http.Controller):
    _return_url = '/account/saltedge/return'

    @http.route([_return_url], type='http', auth='user', methods=['GET'])
    def saltedge_callback(self, **post):

        _logger.error(post)

        wizard_id = request.env["saltedge.wizard"].sudo().create({
            'code': uuid.uuid4()
        })

        return werkzeug.utils.redirect(
            f'/web#id={wizard_id.id}&model=saltedge.wizard&view_type=form&menu_id='
        )


