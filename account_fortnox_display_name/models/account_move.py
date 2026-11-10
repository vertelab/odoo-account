from odoo import models, fields, api


class Account(models.Model):

    _inherit = 'account.move'

    display_name_fortnox = fields.Char(compute="_compute_display_name_fortnox", store=True)

    @api.depends('fortnox_ref', 'name')
    def _compute_display_name_fortnox(self):
        for rec in self:
            if rec.fortnox_ref:
                rec.display_name_fortnox = f"{rec.fortnox_ref}-{rec.name}"
            else:
                rec.display_name_fortnox = rec.name
