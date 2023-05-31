import requests
from odoo import http
from odoo.http import request

class FortnoxController(http.Controller):
    
    @http.route('/fortnox/auth', type='http', auth='public')
    def fortnox_auth(self, **kw):
        # Make the GET request to Fortnox OAuth URL
        response = requests.get('https://apps.fortnox.se/oauth-v1/auth', params={
            'client_id': 'boiM6S7aHLkl',
            'redirect_uri': 'https://5fba-176-10-242-63.ngrok-free.app/fortnox/authvertel.se',
            'response_type': 'code',
            'state': 'something',
            'scope': 'invoice article price offer customer bookkeeping'
        })
        
        # Extract the auth-code from the response URL
        auth_code = response.url.split('code=')[1]

        # Assuming you have a model called 'res.company' with a char field 'fortnox_auth_code'
        company = request.env.user.company_id
        company.fortnox_auth_code = auth_code
        
        return 'Auth code added successfully: {}'.format(auth_code)
#https://5fba-176-10-242-63.ngrok-free.app/fortnox/auth