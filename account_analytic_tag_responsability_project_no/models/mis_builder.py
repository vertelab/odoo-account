from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import traceback
import logging
_logger = logging.getLogger(__name__)

class MisReportInstancePeriod(models.Model):
    _inherit = 'mis.report.instance.period'
    

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
    # ~ def _get_additional_move_line_filter(self):
            # ~ """Prepare a filter to apply on all move lines

            # ~ This filter is applied with a AND operator on all
            # ~ accounting expression domains. This hook is intended
            # ~ to be inherited, and is useful to implement filtering
            # ~ on analytic dimensions or operational units.

            # ~ The default filter is built from a ``mis_report_filters`` context
            # ~ key, which is a list set by the analytic filtering mechanism
            # ~ of the mis report widget::

              # ~ [(field_name, {'value': value, 'operator': operator})]

            # ~ Returns an Odoo domain expression (a python list)
            # ~ compatible with account.move.line."""
            # ~ self.ensure_one()
            # ~ domain = self._get_filter_domain_from_context()
            # ~ if (
                # ~ self._get_aml_model_name() == "account.move.line"
                # ~ and self.report_instance_id.target_move == "posted"
            # ~ ):
                # ~ domain.extend([("move_id.state", "=", "posted")])
            # ~ if self.analytic_account_id:
                # ~ domain.append(("analytic_account_id", "=", self.analytic_account_id.id))
            # ~ if self.analytic_group_id:
                # ~ domain.append(
                    # ~ ("analytic_account_id.group_id", "=", self.analytic_group_id.id)
                # ~ )
            # ~ for tag in self.analytic_tag_ids:
                # ~ domain.append(("analytic_tag_ids", "=", tag.id))
            # ~ return domain
