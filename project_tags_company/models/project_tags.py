from odoo import fields, models


class ProjectTags(models.Model):
    _inherit = 'project.tags'

    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
    )
