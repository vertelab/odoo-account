from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        if len(self.line_ids.filtered(lambda x: not x.project_no and x.display_type != "line_note" and x.display_type != 'line_section' and int(x.account_id.code) >= 3000 and int(x.account_id.code) <= 9999)) > 0:
            raise ValidationError(_("There are lines with an account between 3000 - 9999 that is missing an project tag.\n Add an project tag on these lines before confirming."))
            
        if len(self.line_ids.filtered(lambda x: not x.area_of_responsibility and x.display_type != "line_note" and x.display_type != 'line_section' and int(x.account_id.code) >= 3000 and int(x.account_id.code) <= 9999)) > 0:
            raise ValidationError(_("There are lines with an account between 3000 - 9999 that is missing an area of responsibility tag.\n Add an area of responsibility tag on these lines before confirming."))
        # ~ if len(self.invoice_line_ids.filtered(lambda x: not x.analytic_account_id)) > 0:
            # ~ raise ValidationError(_("Kindly select add an analytic account for all invoice lines"))
        self._post(soft=False)
        return False

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    project_no = fields.Many2one(comodel_name='account.analytic.tag', string='Project Analytic Tag', readonly=False, domain="[('type_of_tag', '=', 'project_number')]")
    area_of_responsibility= fields.Many2one(comodel_name='account.analytic.tag', string='Place Analytic Tag', readonly=False, domain="[('type_of_tag', '=', 'area_of_responsibility')]")
