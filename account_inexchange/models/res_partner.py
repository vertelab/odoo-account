# ~ # -*- coding: utf-8 -*-
# ~ # Part of Odoo. See LICENSE file for full copyright and licensing details.

# ~ from odoo import api, fields, models
# ~ from odoo.exceptions import Warning

# ~ import requests
# ~ import json

# ~ import logging
# ~ _logger = logging.getLogger(__name__)

# ~ class res_partner(models.Model):
    # ~ _inherit = 'res.partner'

    # ~ gln_number_vertel = fields.Char(string = "GLN Number", help = "This is for GLN Number")
    
    # ~ def merge_gln_number(self):
        # ~ for contact in self.env['res.partner'].search([]):
            # ~ _logger.warn(('%s test test ' ) %contact.gln_number)
            # ~ if contact.gln_number:
                # ~ contact.gln_number_vertel = contact.gln_number
                
                
