import requests
from odoo import http
from odoo.http import request
import logging
from werkzeug.utils import redirect
_logger = logging.getLogger(__name__)

class FortnoxController(http.Controller):
    
    @http.route(['/fortnox/auth'], type='http', auth='user')
    def fortnox_auth(self, **kw):
        base_url = request.env["ir.config_parameter"].sudo().get_param("web.base.url")
        if 'run_get' in kw:
            response = requests.get('https://apps.fortnox.se/oauth-v1/auth', params={
                'client_id': 'boiM6S7aHLkl',
                # ~ 'redirect_uri': 'https://154c-176-10-242-63.ngrok-free.app/fortnox/auth',
                'redirect_uri': f"{base_url}/fortnox/auth",
                'response_type': 'code',
                'state': kw['state'],
                'scope': 'invoice article price offer customer bookkeeping'
            })
            
            return redirect(response.url)
        elif 'code' in kw:
            _logger.warning(f"{kw=}")
            auth_code = kw['code']
            company = http.request.env.user.company_id
            company.fortnox_access_token = False
            company.fortnox_refresh_token = False
            company.fortnox_authorization_code = auth_code
                
            http.request.env.user.company_id.fortnox_get_access_token()
            return redirect(f"{base_url}/web#id={kw['state']}&action=52&model=res.company&view_type=form&cids=1&menu_id=4")

