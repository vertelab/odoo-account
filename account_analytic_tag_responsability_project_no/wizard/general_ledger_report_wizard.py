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
        domain = super()._get_account_move_lines_domain()
        # ~ domain = literal_eval(self.domain) if self.domain else []
        if self.project_no:
            domain.append(('project_no','=',self.project_no.id))
        if self.area_of_responsibility:
            domain.append(('area_of_responsibility','=',self.area_of_responsibility.id))
        return domain
        

class GeneralLedgerXslx(models.AbstractModel):
    _inherit = "report.a_f_r.report_general_ledger_xlsx"
    def _get_report_columns(self, report):
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
    def _get_period_ml_data(
            self,
            account_ids,
            partner_ids,
            company_id,
            foreign_currency,
            only_posted_moves,
            date_from,
            date_to,
            partners_data,
            gen_ld_data,
            partners_ids,
            analytic_tag_ids,
            cost_center_ids,
            extra_domain,
        ):
            domain = self._get_period_domain(
                account_ids,
                partner_ids,
                company_id,
                only_posted_moves,
                date_to,
                date_from,
                analytic_tag_ids,
                cost_center_ids,
            )
            if extra_domain:
                domain += extra_domain
            ml_fields = [
                "id",
                "name",
                "date",
                "move_id",
                "journal_id",
                "account_id",
                "partner_id",
                "debit",
                "credit",
                "balance",
                "currency_id",
                "full_reconcile_id",
                "tax_ids",
                "analytic_tag_ids",
                "amount_currency",
                "ref",
                "name",
                "analytic_account_id",
                "project_no",
                "area_of_responsibility",
                
            ]
            move_lines = self.env["account.move.line"].search_read(
                domain=domain, fields=ml_fields
            )
            journal_ids = set()
            full_reconcile_ids = set()
            taxes_ids = set()
            tags_ids = set()
            full_reconcile_data = {}
            acc_prt_account_ids = self._get_acc_prt_accounts_ids(company_id)
            for move_line in move_lines:
                journal_ids.add(move_line["journal_id"][0])
                for tax_id in move_line["tax_ids"]:
                    taxes_ids.add(tax_id)
                for analytic_tag_id in move_line["analytic_tag_ids"]:
                    tags_ids.add(analytic_tag_id)
                if move_line["full_reconcile_id"]:
                    rec_id = move_line["full_reconcile_id"][0]
                    if rec_id not in full_reconcile_ids:
                        full_reconcile_data.update(
                            {
                                rec_id: {
                                    "id": rec_id,
                                    "name": move_line["full_reconcile_id"][1],
                                }
                            }
                        )
                        full_reconcile_ids.add(rec_id)
                acc_id = move_line["account_id"][0]
                ml_id = move_line["id"]
                if move_line["partner_id"]:
                    prt_id = move_line["partner_id"][0]
                    partner_name = move_line["partner_id"][1]
                if acc_id not in gen_ld_data.keys():
                    gen_ld_data = self._initialize_account(
                        gen_ld_data, acc_id, foreign_currency
                    )
                if acc_id in acc_prt_account_ids:
                    if not move_line["partner_id"]:
                        prt_id = 0
                        partner_name = "Missing Partner"
                    partners_ids.append(prt_id)
                    partners_data.update({prt_id: {"id": prt_id, "name": partner_name}})
                    if prt_id not in gen_ld_data[acc_id]:
                        gen_ld_data = self._initialize_partner(
                            gen_ld_data, acc_id, prt_id, foreign_currency
                        )
                    gen_ld_data[acc_id][prt_id][ml_id] = self._get_move_line_data(move_line)
                    gen_ld_data[acc_id][prt_id]["fin_bal"]["credit"] += move_line["credit"]
                    gen_ld_data[acc_id][prt_id]["fin_bal"]["debit"] += move_line["debit"]
                    gen_ld_data[acc_id][prt_id]["fin_bal"]["balance"] += move_line[
                        "balance"
                    ]
                    if foreign_currency:
                        gen_ld_data[acc_id][prt_id]["fin_bal"]["bal_curr"] += move_line[
                            "amount_currency"
                        ]
                else:
                    gen_ld_data[acc_id][ml_id] = self._get_move_line_data(move_line)
                gen_ld_data[acc_id]["fin_bal"]["credit"] += move_line["credit"]
                gen_ld_data[acc_id]["fin_bal"]["debit"] += move_line["debit"]
                gen_ld_data[acc_id]["fin_bal"]["balance"] += move_line["balance"]
                if foreign_currency:
                    gen_ld_data[acc_id]["fin_bal"]["bal_curr"] += move_line[
                        "amount_currency"
                    ]
            journals_data = self._get_journals_data(list(journal_ids))
            accounts_data = self._get_accounts_data(gen_ld_data.keys())
            taxes_data = self._get_taxes_data(list(taxes_ids))
            tags_data = self._get_tags_data(list(tags_ids))
            rec_after_date_to_ids = self._get_reconciled_after_date_to_ids(
                full_reconcile_data.keys(), date_to
            )
            return (
                gen_ld_data,
                accounts_data,
                partners_data,
                journals_data,
                full_reconcile_data,
                taxes_data,
                tags_data,
                rec_after_date_to_ids,
            )
        
    @api.model
    def _get_move_line_data(self, move_line):
        res = super()._get_move_line_data(move_line)
        if not move_line['project_no']:
            res['project_no'] = move_line['project_no']
        else:
            res['project_no'] = move_line['project_no'][1]
            
        if not move_line['area_of_responsibility']:
            res['area_of_responsibility'] = move_line['area_of_responsibility']
        else:
            res['area_of_responsibility'] = move_line['area_of_responsibility'][1]
        return res
        
        # ~ move_line_data = {
            # ~ "id": move_line["id"],
            # ~ "date": move_line["date"],
            # ~ "entry": move_line["move_id"][1],
            # ~ "entry_id": move_line["move_id"][0],
            # ~ "journal_id": move_line["journal_id"][0],
            # ~ "account_id": move_line["account_id"][0],
            # ~ "partner_id": move_line["partner_id"][0]
            # ~ if move_line["partner_id"]
            # ~ else False,
            # ~ "partner_name": move_line["partner_id"][1]
            # ~ if move_line["partner_id"]
            # ~ else "",
            # ~ "ref": "" if not move_line["ref"] else move_line["ref"],
            # ~ "name": "" if not move_line["name"] else move_line["name"],
            # ~ "tax_ids": move_line["tax_ids"],
            # ~ "debit": move_line["debit"],
            # ~ "credit": move_line["credit"],
            # ~ "balance": move_line["balance"],
            # ~ "bal_curr": move_line["amount_currency"],
            # ~ "rec_id": move_line["full_reconcile_id"][0]
            # ~ if move_line["full_reconcile_id"]
            # ~ else False,
            # ~ "rec_name": move_line["full_reconcile_id"][1]
            # ~ if move_line["full_reconcile_id"]
            # ~ else "",
            # ~ "tag_ids": move_line["analytic_tag_ids"],
            
            # ~ "currency_id": move_line["currency_id"],
            # ~ "analytic_account": move_line["analytic_account_id"][1]
            # ~ if move_line["analytic_account_id"]
            # ~ else "",
            # ~ "analytic_account_id": move_line["analytic_account_id"][0]
            # ~ if move_line["analytic_account_id"]
            # ~ else False,
        # ~ }
        # ~ if (
            # ~ move_line_data["ref"] == move_line_data["name"]
            # ~ or move_line_data["ref"] == ""
        # ~ ):
            # ~ ref_label = move_line_data["name"]
        # ~ elif move_line_data["name"] == "":
            # ~ ref_label = move_line_data["ref"]
        # ~ else:
            # ~ ref_label = move_line_data["ref"] + str(" - ") + move_line_data["name"]
        # ~ move_line_data.update({"ref_label": ref_label})
        # ~ return move_line_data
