import time
from ast import literal_eval

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import date_utils
import logging
_logger = logging.getLogger(__name__)

class GeneralLedgerReportWizard(models.TransientModel):
    """General Ledger report wizard."""

    _inherit = "general.ledger.report.wizard"
    
    project_no = fields.Many2one(comodel_name='account.analytic.tag', string='Project', readonly=False,
                                 domain="[('type_of_tag', '=', 'project_number')]")
    area_of_responsibility = fields.Many2one(comodel_name='account.analytic.tag', string='Cost Center',
                                             readonly=False, domain="[('type_of_tag', '=', 'area_of_responsibility')]")
    def _prepare_report_general_ledger(self):
        res = super()._prepare_report_general_ledger()
        res["project_no"] = self.project_no
        res["area_of_responsibility"] = self.area_of_responsibility
        return res
    
    def _get_account_move_lines_domain(self):
        _logger.warning("_get_account_move_lines_domain"*100)
        domain = super()._get_account_move_lines_domain()
        # ~ domain = literal_eval(self.domain) if self.domain else []
        if self.project_no:
            domain.append(('project_no','=',self.project_no.id))
        if self.area_of_responsibility:
            domain.append(('area_of_responsibility','=',self.area_of_responsibility.id))
        _logger.warning(f"{domain=}")
        return domain
        

class GeneralLedgerXslx(models.AbstractModel):
    _inherit = "report.a_f_r.report_general_ledger_xlsx"
    def _get_report_columns(self, report):
        _logger.warning("_get_report_columns"*100)
        res = [
            {"header": _("Date"), "field": "date", "width": 11},
            {"header": _("Entry"), "field": "entry", "width": 18},
            {"header": _("Journal"), "field": "journal", "width": 8},
            {"header": _("Account"), "field": "account", "width": 9},
            {"header": _("Taxes"), "field": "taxes_description", "width": 15},
            {"header": _("Partner"), "field": "partner_name", "width": 25},
            {"header": _("Ref - Label"), "field": "ref_label", "width": 40},
        ]
        if report.show_cost_center:
            res += [
                {
                    "header": _("Analytic Account"),
                    "field": "analytic_account",
                    "width": 20,
                },
            ]
        if report.show_analytic_tags:
            # ~ res += [
                # ~ {"header": _("Tags"), "field": "tags", "width": 10},
            # ~ ]
            
            res += [
                {"header": _("Project"), "field": "project_no", "width": 10},
            ]
            
            res += [
                {"header": _("Cost Center"), "field": "area_of_responsibility", "width": 10},
            ]
        res += [
            {"header": _("Rec."), "field": "rec_name", "width": 15},
            {
                "header": _("Debit"),
                "field": "debit",
                "field_initial_balance": "initial_debit",
                "field_final_balance": "final_debit",
                "type": "amount",
                "width": 14,
            },
            {
                "header": _("Credit"),
                "field": "credit",
                "field_initial_balance": "initial_credit",
                "field_final_balance": "final_credit",
                "type": "amount",
                "width": 14,
            },
            {
                "header": _("Cumul. Bal."),
                "field": "balance",
                "field_initial_balance": "initial_balance",
                "field_final_balance": "final_balance",
                "type": "amount",
                "width": 14,
            },
        ]
        if report.foreign_currency:
            res += [
                {
                    "header": _("Cur."),
                    "field": "currency_name",
                    "field_currency_balance": "currency_name",
                    "type": "currency_name",
                    "width": 7,
                },
                {
                    "header": _("Amount cur."),
                    "field": "bal_curr",
                    "field_initial_balance": "initial_bal_curr",
                    "field_final_balance": "final_bal_curr",
                    "type": "amount_currency",
                    "width": 14,
                },
            ]
        res_as_dict = {}
        for i, column in enumerate(res):
            res_as_dict[i] = column
        return res_as_dict
        
class GeneralLedgerReport(models.AbstractModel):
    _inherit = "report.account_financial_report.general_ledger"
    def _get_report_values(self, docids, data):
        #_logger.warning("_get_report_values inherit" *100)
        res = super()._get_report_values(docids, data)
        if 'general_ledger' in res:
            for account in res['general_ledger']:
                if 'move_lines' in account:
                    for line in account['move_lines']:
                        real_line = self.env['account.move.line'].browse(line['id'])
                        line['project_no'] = real_line.project_no
                        line['area_of_responsibility'] = real_line.area_of_responsibility
                        # ~ _logger.warning(f"{line=}")
                if 'list_partner' in account:
                    for partner in account['list_partner']:
                        if 'move_lines' in partner:
                            for line in partner['move_lines']:
                                real_line = self.env['account.move.line'].browse(line['id'])
                                line['project_no'] = real_line.project_no
                                line['area_of_responsibility'] = real_line.area_of_responsibility
                        
                        
        return res
