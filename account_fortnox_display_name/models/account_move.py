from odoo import models, fields, api

class Account(models.Model):

    _inherit = 'account.move'
    _description = 'Replaces name with the fortnox ref dash name if there is a fortnox ref'

    display_name_fortnox = fields.Char(compute="_compute_display_name_fortnox", store=True)

    @api.onchange('fortnox_ref','name')
    def _compute_display_name_fortnox(self):
        for rec in self:    
            if rec.fortnox_ref: 
                rec.display_name_fortnox = f"{rec.fortnox_ref}-{rec.name}"
            else: 
                rec.display_name_fortnox = rec.name