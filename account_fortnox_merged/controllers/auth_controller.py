import requests
from odoo import http
from odoo.http import request
import logging
_logger = logging.getLogger(__name__)

class FortnoxController(http.Controller):
    
    @http.route('/fortnox/auth', type='http', auth='public')
    def fortnox_auth(self, **kw):
        # Make the GET request to Fortnox OAuth URL
        if 'run_get' in kw:    
            response = requests.get('https://apps.fortnox.se/oauth-v1/auth', params={
                'client_id': 'boiM6S7aHLkl',
                'redirect_uri': 'https://34f3-176-10-242-63.ngrok-free.app/fortnox/auth',
                'response_type': 'code',
                'state': 'something',
                'scope': 'invoice article price offer customer bookkeeping'
                })
                
            return { 
                'type': 'ir.actions.act_url',
                'url': response.url,
                'target': 'new',
            }
        else:
            # Extract the auth-code from the response URL
            auth_code = kw.url.split('code=')[1]

            # Assuming you have a model called 'res.company' with a char field 'fortnox_auth_code'
            company = http.request.env.user.company_id
            company.fortnox_authorization_code = auth_code
        
            return 'Auth code added successfully: {}'.format(auth_code)
