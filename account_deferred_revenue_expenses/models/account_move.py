import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tests.common import Form

_logger = logging.getLogger(__name__)


FIELDS_AFFECTS_ASSET_MOVE_LINE = {
    "credit",
    "debit",
    "account_id",
    "journal_id",
    "date",
    "asset_profile_id",
    "deferred_expense_profile_id",
    "asset_id",
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    deferred_expense_count = fields.Integer(compute="_compute_asset_count")

    def _compute_asset_count(self):
        super(AccountMoveLine, self)._compute_asset_count()

        for move in self:
            move.asset_count =len(move.invoice_line_ids.filtered(lambda l: l.asset_profile_id.id != False) )
            move.deferred_expense_count =len(move.invoice_line_ids.filtered(lambda l: l.deferred_expense_profile_id.id != False) )

    def _prepare_asset_vals(self, aml):
        depreciation_base = aml.balance
        return {
            "name": aml.name,
            "code": self.name,
            "profile_id": aml.asset_profile_id or aml.deferred_expense_profile_id,
            "purchase_value": depreciation_base,
            "partner_id": aml.partner_id,
            "date_start": self.date,
        }

    def action_post(self):
        ret_val = super().action_post()
        for move in self:
            for aml in move.line_ids.filtered(
                lambda line: (line.asset_profile_id or line.deferred_expense_profile_id) and not line.tax_line_id
            ):
                vals = move._prepare_asset_vals(aml)
                if not aml.name:
                    raise UserError(
                        _("Asset name must be set in the label of the line.")
                    )
                if aml.asset_id:
                    aml.asset_id.rec_type = aml.asset_profile_id.rec_type or aml.deferred_expense_profile_id.rec_type
                    continue
                asset_form = Form(
                    self.env["account.asset"]
                    .with_company(move.company_id)
                    .with_context(create_asset_from_move_line=True, move_id=move.id)
                )
                for key, val in vals.items():
                    setattr(asset_form, key, val)
                asset = asset_form.save()
                asset.rec_type = aml.asset_profile_id.rec_type or aml.deferred_expense_profile_id.rec_type

                asset.analytic_distribution = aml.analytic_distribution
                aml.with_context(
                    allow_asset=True, allow_asset_removal=True
                ).asset_id = asset.id
            refs = [
                "<a href=# data-oe-model=account.asset data-oe-id=%s>%s</a>"
                % tuple(name_get)
                for name_get in move.line_ids.filtered(
                    "asset_profile_id" or "deferred_expense_profile_id"
                ).asset_id.name_get()
            ]
            if refs:
                message = _("This invoice created the asset(s): %s") % ", ".join(refs)
                move.message_post(body=message)
        return ret_val

    def button_view_deferred_expenses(self):
        view_tree_id = self.env.ref('account_deferred_revenue_expenses.account_deferred_expense_view_tree')
        view_form_id = self.env.ref('account_deferred_revenue_expenses.account_deferred_expense_form_view')

        if res_id := self.env['account.asset'].search([('code', '=', self.name), ('rec_type', '=', 'deferred_expense')]):
            return {
                'name': _('Deferred Expense'),
                'res_model': 'account.asset',
                'view_mode': 'form',
                # 'view_id': view_form_id.id,
                'views': [(view_form_id.id, 'form')],
                'type': 'ir.actions.act_window',
                'res_id': res_id.id

            }

    def button_view_assets(self):
        if res_id := self.env['account.asset'].search([('code', '=', self.name), ('rec_type', '=', 'asset')]):
            return {
                'name': _('Assets'),
                'res_model': 'account.asset',
                'view_mode': 'form',
                'context': {
                    'default_rec_type': 'asset',
                },
                # 'domain': [('rec_type', '=', 'asset')],
                'type': 'ir.actions.act_window',
                'res_id': res_id.id
            }

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    deferred_expense_profile_id = fields.Many2one('account.asset.profile', string="Accural",
                                                  domain=[('rec_type', '=', 'deferred_expense')])
    asset_profile_id = fields.Many2one(comodel_name="account.asset.profile", string="Asset Profile", store=True,
                                       readonly=False,)

    
    def _compute_asset_profile(self):
        pass

    def write(self, vals):
        if set(vals).intersection(FIELDS_AFFECTS_ASSET_MOVE_LINE) and not (
                self.env.context.get("allow_asset_removal")
                and list(vals.keys()) == ["asset_id"]
        ):
            # Check if at least one asset is linked to a move
            linked_asset = False
            for move_line in self.filtered(lambda r: not r.move_id.is_sale_document()):
                linked_asset = move_line.asset_id
                if linked_asset:
                    raise UserError(
                        _(
                            "You cannot change an accounting item "
                            "linked to an asset depreciation line."
                        )
                    )

        if (
                self.filtered(lambda r: not r.move_id.is_sale_document())
                and vals.get("asset_id")
                and not self.env.context.get("allow_asset")
        ):
            raise UserError(
                _(
                    "You are not allowed to link "
                    "an accounting entry to an asset."
                    "\nYou should generate such entries from the asset."
                )
            )
        super().write(vals)
        if "quantity" in vals or "asset_profile_id" in vals or "deferred_expense_profile_id" in vals:
            for record in self:
                record._expand_asset_line()
        return True

    def _expand_asset_line(self):
        self.ensure_one()
        if (self.asset_profile_id or self.deferred_expense_profile_id) and self.quantity > 1.0:
            profile = self.asset_profile_id or self.deferred_expense_profile_id
            if profile.asset_product_item:
                aml = self.with_context(check_move_validity=False)
                qty = self.quantity
                name = self.name
                aml.write({"quantity": 1, "name": "{} {}".format(name, 1)})
                for i in range(1, int(qty)):
                    aml.copy({"name": "{} {}".format(name, i + 1)})

    
    @api.onchange('product_id')
    def _compute_deferred_expense(self):
        # ~ _logger.warning("_compute_deferred_expense"*100)
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue
            line.deferred_expense_profile_id= line.product_id.deferred_expense_profile_id.id
