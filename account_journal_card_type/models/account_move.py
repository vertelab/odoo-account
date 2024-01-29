from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.constrains('journal_id', 'move_type')
    def _check_journal_move_type(self):
        for move in self:
            if move.is_purchase_document(include_receipts=True) and move.journal_id.type not in ['purchase','card']:
                raise ValidationError(_("Cannot create a purchase document in a non purchase journal"))
            if move.is_sale_document(include_receipts=True) and move.journal_id.type != 'sale':
                raise ValidationError(_("Cannot create a sale document in a non sale journal"))
