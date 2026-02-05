import logging

from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError, AccessError, ValidationError

_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = "account.journal"

    def create_document_from_attachment(self,attachment_ids):
    
        _logger.error(f"{attachment_ids=}")

        if self:
            company_id = self.company_id.id
        else:
            company_id = self.env.company.id

        ai_wiz = self.env["account.invoice.import"].create(
                {
                    "company_id": company_id,
                    "invoice_attachment_ids": [Command.set(attachment_ids)],
                }
            )
        action, move_ids, faild_attachments_ids = ai_wiz.import_invoices_ai()

        _logger.error(f"{move_ids=}")

        if faild_attachments_ids:
            wiz = self.env["account.invoice.import"].create(
                {
                    "company_id": company_id,
                    "invoice_attachment_ids": [Command.set(faild_attachments_ids)],
                }
            )
            failed_action = wiz.import_invoices()

            # Updates the action depending on if its one move or many on the failed one.
            if (next_action := failed_action.get("next_action", {})):

                if res_id := next_action.pop("res_id"):              
                    move_ids.append(res_id)

                _logger.error(f"{action["next_action"]["domain"][0][2]=}")
                _logger.error(f"{next_action["domain"][0][2]=}")
                _logger.error(f"{move_ids=}")

                action["next_action"]["domain"][0][2] = next_action["domain"][0][2] + move_ids

                _logger.error(f"{action["next_action"]["domain"][0][2]=}")

           
        return action
            





