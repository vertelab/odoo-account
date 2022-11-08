from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import traceback
import logging

_logger = logging.getLogger(__name__)


class MisReportInstance(models.Model):
    _inherit = 'mis.report.instance'

    area_of_responsibility = fields.Many2one("account.analytic.tag", string="Area Of Responsibility",
                                             domain="[('type_of_tag', '=', 'area_of_responsibility')]")
    project_no = fields.Many2one("account.analytic.tag", string="Project Number",
                                 domain="[('type_of_tag', '=', 'project_number')]")


class MisReportInstancePeriod(models.Model):
    _inherit = 'mis.report.instance.period'

    def _get_additional_move_line_filter(self):
        domain = super(MisReportInstancePeriod, self)._get_additional_move_line_filter()
        if self.report_instance_id.area_of_responsibility:
            domain.extend([("area_of_responsibility", "=", self.report_instance_id.area_of_responsibility.id)])
        if self.report_instance_id.project_no:
            domain.extend([("project_no", "=", self.report_instance_id.project_no.id)])
        return domain
