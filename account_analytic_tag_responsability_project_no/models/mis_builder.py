from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import traceback
import logging
_logger = logging.getLogger(__name__)

class MisReportInstancePeriod(models.Model):
    _inherit = 'mis.report.instance.period'
    
    #area_of_responsibility = fields.One2many("account.analytic.tag","Area Of Responsibility")
    #project_no = fields.One2many("account.analytic.tag","Project Number")


    def _get_additional_move_line_filter(self):
        domains = super(MisReportInstancePeriod, self)._get_additional_move_line_filter()
        new_domain_without_analytic_tag_ids = []
        _logger.warning(f"{new_domain_without_analytic_tag_ids=}")
        for domain in domains:
            if "analytic_tag_ids" in domain:
                tag_id = domain[2]
                _logger.warning(f"{tag_id=} {domain=}")
                if self.env['account.analytic.tag'].browse(tag_id).type_of_tag == "area_of_responsibility":
                    new_domain_without_analytic_tag_ids.append(("area_of_responsibility", "=", tag_id))
                if self.env['account.analytic.tag'].browse(tag_id).type_of_tag == "project_number":
                    new_domain_without_analytic_tag_ids.append(("project_no", "=", tag_id))
            else:
                new_domain_without_analytic_tag_ids.append(domain)
        
        return new_domain_without_analytic_tag_ids
