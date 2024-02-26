
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MisBudgetItemAbstract(models.AbstractModel):
    _name = "mis.budget.item.abstract"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'mis.budget.item.abstract']

    partner_id = fields.Many2one('res.partner', string="Partner")
    #employee_id = fields.Many2one('hr.employee', string="Employee")
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done'), ('cancelled', 'Cancelled')], string="State")


