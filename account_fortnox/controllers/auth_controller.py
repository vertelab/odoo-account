import base64
import logging

import requests
from werkzeug.utils import redirect

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

FORTNOX_AUTH_URL = 'https://apps.fortnox.se/oauth-v1/auth'
FORTNOX_SCOPES = 'invoice article price offer customer bookkeeping settings inbox connectfile archive'


def _encode_state(company_id, db):
    """Encode company + db into an opaque OAuth state parameter."""
    raw = f'{company_id}:{db}'
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_state(state):
    """Decode the state parameter into (company_id, db)."""
    try:
        raw = base64.urlsafe_b64decode(state.encode()).decode()
        company_id, db = raw.rsplit(':', 1)
        return int(company_id), db
    except Exception:
        return int(state), None


class FortnoxController(http.Controller):

    @http.route(['/fortnox/auth'], type='http', auth='user')
    def fortnox_auth(self, **kw):
        base_url = request.env["ir.config_parameter"].sudo().get_param("web.base.url")

        if 'run_get' in kw:
            # auth='user' keeps Odoo's own access check on res.company.
            company = request.env["res.company"].browse(int(kw['state']))
            if not company.fortnox_client_id:
                return request.make_response(
                    'Fel: Fortnox Client ID saknas på företaget. Fyll i den under '
                    'Inställningar > Företag > Fortnox Integration.',
                    headers=[('Content-Type', 'text/plain; charset=utf-8')],
                )

            response = requests.get(FORTNOX_AUTH_URL, params={
                'client_id': company.fortnox_client_id,
                'redirect_uri': f"{base_url}/fortnox/auth",
                'response_type': 'code',
                'state': _encode_state(company.id, request.db),
                'scope': FORTNOX_SCOPES,
                'access_type': 'offline',
            })

            return redirect(response.url)

        elif 'code' in kw:
            auth_code = kw['code']
            company_id, db = _decode_state(kw.get('state', ''))
            if db and db != request.db:
                _logger.warning("Fortnox OAuth callback for db %s, current db %s", db, request.db)
                return request.make_response(
                    'Fel: auktoriseringen gjordes i en annan databas.',
                    headers=[('Content-Type', 'text/plain; charset=utf-8')],
                )

            company = request.env["res.company"].browse(company_id)
            company.fortnox_access_token = False
            company.fortnox_refresh_token = False
            company.fortnox_authorization_code = auth_code

            company.fortnox_get_access_token()
            return redirect(f"{base_url}/web#id={company_id}&model=res.company&view_type=form")

        return request.not_found()
