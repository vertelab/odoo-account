# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import http
from odoo.http import request
import werkzeug
import json

_logger = logging.getLogger(__name__)


class FintectureController(http.Controller):
    _return_url = '/account/fintecture/return'

    @http.route([_return_url], type='http', auth='user', methods=['GET'])
    def fintecture_callback(self, **params):
        wizard_id = request.env["fintecture.wizard"].sudo().create({
            'code': params.get('code'),
            'fintecture_customer_id': params.get('customer_id')
        })

        return werkzeug.utils.redirect(
            f'/web#id={wizard_id.id}&model=fintecture.wizard&view_type=form&menu_id='
        )


