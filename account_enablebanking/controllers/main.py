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
    _payment_return_url = '/account/enable-banking/payment-return'

    @http.route([_return_url], type='http', auth='user', methods=['GET'])
    def enable_banking_callback(self, **post):
        wizard_id = request.env["enable.banking.wizard"].sudo().create({
            'code': post.get('code'),
        })

        return werkzeug.utils.redirect(
            f'/web#id={wizard_id.id}&model=enable.banking.wizard&view_type=form&menu_id='
        )

    @http.route([_payment_return_url], type='http', auth='user', methods=['GET'])
    def enable_banking_payment_callback(self, **kwargs):
        """Handle return from Enable Banking payment authorization."""
        error = kwargs.get('error')
        payment_id = kwargs.get('payment_id')
        state = kwargs.get('state')

        if error:
            error_desc = kwargs.get('error_description', 'Unknown error')
            _logger.error("Payment authorization error: %s - %s", error, error_desc)
            # Find the pending payment and mark as rejected
            payments = request.env['enable.banking.payment'].sudo().search(
                [('state', '=', 'pending_authorization')],
                order='create_date desc', limit=1
            )
            if payments:
                payments.write({
                    'state': 'rejected',
                    'error_message': f"{error}: {error_desc}",
                })
            return werkzeug.utils.redirect(
                f'/web#model=enable.banking.payment&view_type=list&action=account_enablebanking.action_enable_banking_payment'
            )

        # Payment authorized — update status
        if payment_id:
            payment = request.env['enable.banking.payment'].sudo().search(
                [('enable_banking_payment_id', '=', payment_id)], limit=1
            )
            if payment:
                payment.write({'state': 'authorized'})
                return werkzeug.utils.redirect(
                    f'/web#id={payment.id}&model=enable.banking.payment&view_type=form'
                )

        return werkzeug.utils.redirect('/web')


