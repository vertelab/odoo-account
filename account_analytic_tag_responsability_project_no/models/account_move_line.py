from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import traceback
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"
     
    def request_validation(self):
        if len(self.line_ids.filtered(
                lambda x: not x.area_of_responsibility and x.display_type != "line_note" and x.display_type != 'line_section' and int(
                        x.account_id.code) >= 3000 and int(x.account_id.code) <= 9999)) > 0:
            raise ValidationError(
                _("There are lines with an account between 3000 - 9999 that is missing an Cost Center "
                  "tag.\n Add an Cost Center tag on these lines before requesting a validation."))
        
        return super(AccountMove, self).request_validation()
     
    def action_post(self):
        # if len(self.line_ids.filtered(lambda x: not x.project_no and x.display_type != "line_note" and
        # x.display_type != 'line_section' and int(x.account_id.code) >= 3000 and int(x.account_id.code) <= 9999)) >
        # 0: raise ValidationError(_("There are lines with an account between 3000 - 9999 that is missing an project
        # tag.\n Add an project tag on these lines before confirming."))

        if len(self.line_ids.filtered(
                lambda x: not x.area_of_responsibility and x.display_type != "line_note" and x.display_type != 'line_section' and int(
                        x.account_id.code) >= 3000 and int(x.account_id.code) <= 9999)) > 0:
            raise ValidationError(
                _("There are lines with an account between 3000 - 9999 that is missing an Cost Center "
                  "tag.\n Add an Cost Center tag on these lines before confirming."))

        return super(AccountMove, self).action_post()

        # ~ if len(self.invoice_line_ids.filtered(lambda x: not x.analytic_account_id)) > 0:
        # ~ raise ValidationError(_("Kindly select add an analytic account for all invoice lines"))
        # ~ self._post(soft=False)
        # ~ return False

    def _post(self, soft=True):
        # # This function is used in the background, so there are places i can't predict where odoo will create an
        # invoice with lines that are missing project or Cost Center.
        icp = self.env['ir.config_parameter'].sudo()
        harsher_check = icp.get_param('account_analytic_tag_responsability_project_no.hard_invoice_account_check',
                                      default=False)
        if harsher_check:
            # if len(self.line_ids.filtered(lambda x: not x.project_no and x.display_type != "line_note" and
            # x.display_type != 'line_section' and int(x.account_id.code) >= 3000 and int(x.account_id.code) <=
            # 9999)) > 0: raise ValidationError(_("There are lines with an account between 3000 - 9999 that is
            # missing an project tag.\n Add an project tag on these lines before confirming. \n If this check in in
            # the way you can disable it by going to the settings and disabling Harsh Analytic Tag Enforcement"))

            if len(self.line_ids.filtered(
                    lambda x: not x.area_of_responsibility and x.display_type != "line_note" and x.display_type != 'line_section' and int(
                            x.account_id.code) >= 3000 and int(x.account_id.code) <= 9999)) > 0:
                raise ValidationError(
                    _("There are lines with an account between 3000 - 9999 that is missing an Cost Center "
                      "tag.\n Add an Cost Center tag on these lines before confirming. \n If this check in "
                      "in the way you can disable it by going to the settings and disabling Harsh Analytic Tag "
                      "Enforcement"))
        else:
            if len(self.line_ids.filtered(
                    lambda x: not x.project_no and x.display_type != "line_note" and x.display_type != 'line_section' and int(
                            x.account_id.code) >= 3000 and int(x.account_id.code) <= 9999)) > 0:
                _logger.warning(f"harsher_check on project tag disabled but triggerd on {self}")
                _logger.warning("".join(traceback.format_stack()))
            if len(self.line_ids.filtered(
                    lambda x: not x.area_of_responsibility and x.display_type != "line_note" and x.display_type != 'line_section' and int(
                            x.account_id.code) >= 3000 and int(x.account_id.code) <= 9999)) > 0:
                _logger.warning(f"harsher_check on a Cost Center disabled but triggerd on {self}")
                _logger.warning("".join(traceback.format_stack()))
        return super(AccountMove, self)._post(soft)

    def action_add_project_and_cost_center_wizard(self):
        view_id = self.env.ref(
            'account_analytic_tag_responsability_project_no.choose_project_number_and_cost_center_view_form').id

        name = _('Add Project and Cost Center to Invoice Lines')

        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'project.cost.center.wizard',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': {
                'default_res_id': self.id,
                'default_res_model': self._name,
            }
        }
        
    @api.onchange('purchase_vendor_bill_id', 'purchase_id')
    def _onchange_purchase_auto_complete(self):
        vals = super()._onchange_purchase_auto_complete()
        for move in self:
            for line in move.line_ids:
                    if line.purchase_line_id:
                            line.project_no = line.purchase_line_id.project_no
                            line.area_of_responsibility = line.purchase_line_id.area_of_responsibility


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    project_no = fields.Many2one(comodel_name='account.analytic.tag', string='Project', readonly=False,
                                 domain="[('type_of_tag', '=', 'project_number')]")
    area_of_responsibility = fields.Many2one(comodel_name='account.analytic.tag', string='Cost Center',
                                             readonly=False, domain="[('type_of_tag', '=', 'area_of_responsibility')]")

    def reconcile(self):
        res = super(AccountMoveLine, self).reconcile()
        if res and "partials" in res:
            for partial_record in res['partials']:

                move_with_tags = False
                move_without_tags = False

                if partial_record.debit_move_id.move_id.move_type == "entry":
                    move_with_tags = partial_record.credit_move_id.move_id
                    move_without_tags = partial_record.debit_move_id.move_id

                if partial_record.credit_move_id.move_id.move_type == "entry":
                    move_with_tags = partial_record.debit_move_id.move_id
                    move_without_tags = partial_record.credit_move_id.move_id
                if move_with_tags and move_without_tags:

                    # ~ if partial_record.debit_move_id.move_id.move_type == "entry" and
                    # partial_record.credit_move_id.move_id.move_type == "in_invoice":
                    tags = []
                    area_of_responsibility = False
                    project_no = False
                    for line in move_with_tags.line_ids:
                        for tag in line.analytic_tag_ids:
                            tags.append((4, tag.id, 0))

                        if line.project_no:
                            project_no = line.project_no
                        if line.area_of_responsibility:
                            area_of_responsibility = line.area_of_responsibility

                    for line in move_without_tags.line_ids:
                        if 3000 <= int(line.account_id.code) <= 9999:
                            if not line.project_no:
                                line.project_no = project_no
                            if not line.area_of_responsibility:
                                line.area_of_responsibility = area_of_responsibility
                            line.write({'analytic_tag_ids': tags})
        return res
