import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError

_logger = logging.getLogger(__name__)

class AccountInvoiceImport(models.TransientModel):
    _inherit = "account.invoice.import"

    def import_invoices_ai(self):
        """Method called by the button of the wizard"""
        self.ensure_one()
        company = self.company_id
        if not self.invoice_attachment_ids:
            raise UserError(_("You must select the vendor bills to import."))

        successfull_moves, faild_move_attachments = self.ai_2_move(self.invoice_attachment_ids)

        next_action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_in_invoice_type"
        )

        next_action["domain"] = [("id", "in", successfull_moves)]

        action = {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("Import Vendor Bills"),
                "message": _("%d vendor bill(s) created", len(successfull_moves)),
                "next": next_action,
            },
        }
        return action, successfull_moves, faild_move_attachments

    def ai_2_move(self,attachment_ids):
        
        quest_id = self.env["ai.quest"].search([("ai_type", "=", "account-invoice-pdf")],limit=1)
        
        _logger.error(f"{quest_id=}")

        if quest_id:

            vendor_finder_candidates = quest_id.ai_agent_ids.filtered(lambda a: a.ai_agent_id.ai_type == "vendor-finder")
            vendor_finder_agent_id = vendor_finder_candidates[0].ai_agent_id if vendor_finder_candidates else quest_id.ai_agent_ids[0].ai_agent_id
            
            faild_move_attachments = []
            successfull_moves = [] 

            for attachment_id in attachment_ids:

                session_id = self.env["ai.quest.session"].quest_init(quest_id)

                pdf_text = attachment_id.get_pdf_content()

                _logger.error(f"{pdf_text=}")

                partner_id = quest_id.find_partner_based_on_vat(pdf_text)
                if not partner_id:
                    partner_id = quest_id.find_partner_based_on_keyword(pdf_text)
                if  not partner_id:
                    
                    partner_json = vendor_finder_agent_id.trigger_prompt(
                    quest=quest_id,
                    session=session_id,
                    debug=quest_id.debug,
                    message=pdf_text,
                    )
                    _logger.warning(f"{partner_json=}")
                    partner_id = quest_id.partner_search(session_id, partner_json.content)
                    _logger.warning(f"{partner_id=}")
                    if not partner_id:
                       partner_id = quest_id.partner_create(session_id, partner_json.content)
                move = quest_id._process_file_content(session_id, partner_id, pdf_text, match_purchase_order=False)

                session_id.write({"status": "done"})

                if move:
                    quest_id._set_to_check_vendor_bill(move)
                    attachment_id.write({"res_id": move.id, "res_model": move._name})
                    successfull_moves.append(move.id)
                else:
                    faild_move_attachments.append(attachment_id.id)


            return (successfull_moves, faild_move_attachments)
            

            
        return (attachment_ids, attachment_ids)
        
