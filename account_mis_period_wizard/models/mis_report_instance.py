from odoo import api, fields, models, _

class MisReportInstance(models.Model):

    _inherit = "mis.report.instance"

    #comparison_mode = fields.Boolean(string="Comparison Mode", default = True)
    date_from = fields.Date(string="From", default=fields.Date.today())
    date_to = fields.Date(string="To", default=fields.Date.today())