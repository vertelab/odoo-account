from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"
    @api.model
    def create(self, values):
        res = super(AccountMove, self).create(values)
        for record in res.line_ids:
            if record.analytic_tag_ids:
                record._depends_analytic_tag_ids()
        return res

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
         
    def _default_project_tag(self):
        # ~ _logger.warning("_default_project_tag")
        # ~ _logger.warning(f"{self=}")
        for tag in self.analytic_tag_ids:
            # ~ _logger.warning(f"tag.type_of_tag:{tag.type_of_tag}")
            if tag.type_of_tag == "project_number":
               # ~ _logger.warning("_default_project_tag TRUE")
               return tag
        return False
    
    def _default_place_tag(self):
        # ~ _logger.warning("_default_place_tag")
        # ~ _logger.warning(f"{self=}")
        for tag in self.analytic_tag_ids:
            # ~ _logger.warning(f"tag.type_of_tag:{tag.type_of_tag}")
            if tag.type_of_tag == "area_of_responsibility":
               # ~ _logger.warning("_default_place_tag TRUE")
               # ~ _logger.warning(f"place tag id = {tag.id}")
               return tag
        return False
        
        
    def write(self, values):
        # ~ _logger.warning("AccountMoveLine write")
        res = super(AccountMoveLine, self).write(values)
        if values.get('analytic_tag_ids'):
            # ~ _logger.warning("AccountMoveLine write analytic_tag_ids")
            self._depends_analytic_tag_ids()
        return res
            
        
    @api.depends("analytic_tag_ids")
    def _depends_analytic_tag_ids(self):
        # ~ _logger.warning("_depends_analytic_tag_ids")
        for record in self:
            if record.move_id.period_id.state == "draft":
                # ~ _logger.warning(f"{record=}")
                record.project_no = record._default_project_tag()
                # ~ _logger.warning(record.project_no)
                record.area_of_responsibility = record._default_place_tag()
                # ~ _logger.warning(record.area_of_responsibility)
                    

    project_no = fields.Many2one(comodel_name='account.analytic.tag', string='Project Analytic Tag', default=_default_project_tag, readonly=True)
    area_of_responsibility= fields.Many2one(comodel_name='account.analytic.tag', string='Place Analytic Tag', default=_default_place_tag, readonly=True)


class AccountAnalyticTag(models.Model):
    _inherit = "account.analytic.tag"

    def write(self, values):
        res = super(AccountAnalyticTag, self).write(values)
        for record in self:
            move_line_records = self.env['account.move.line'].search([('analytic_tag_ids','in',record.id)])
            move_line_records._depends_analytic_tag_ids()
        return res
                
    # ~ @api.onchange("analytic_tag_ids")
    # ~ def _compute_place_tag(self):
        # ~ _logger.warning("_compute_place_tag")
        # ~ _logger.warning(f"{self=}")
        # ~ for record in self:
            # ~ for tag in record.analytic_tag_ids:
                # ~ _logger.warning(f"tag.type_of_tag:{tag.type_of_tag}")
                # ~ if tag.type_of_tag == "place_of_responsibility":
                   # ~ _logger.warning("_compute_place_tag TRUE")
                   # ~ record.place_of_responsability = tag.id
                   # ~ break
            # ~ _logger.warning("Tag Check FALSE")
            # ~ _logger.warning(record.place_of_responsability)
            # ~ if not record.place_of_responsability:
                # ~ _logger.warning("_compute_place_tag FALSE")
                # ~ record.project_no = False
                 
    # ~ @api.onchange("analytic_tag_ids")
    # ~ def _compute_project_tag(self):
        # ~ _logger.warning("_compute_project_tag")
        # ~ _logger.warning(f"{self=}")
        # ~ for record in self:
            # ~ for tag in record.analytic_tag_ids:
                # ~ _logger.warning(f"tag.type_of_tag:{tag.type_of_tag}")
                # ~ if tag.type_of_tag == "project_number":
                   # ~ _logger.warning("_compute_project_tag TRUE")
                   # ~ record.project_no = tag.id
                   # ~ break
            # ~ if not record.project_no:
                # ~ _logger.warning("_compute_project_tag FALSE")
                # ~ record.project_no = False
                   
    # ~ project_no = fields.Many2one(comodel_name='account.analytic.tag', string='Project Analytic Tag', compute='_compute_project_tag')
    # ~ place_of_responsability = fields.Many2one(comodel_name='account.analytic.tag', string='Place Analytic Tag', compute='_compute_place_tag')
    
    # ~ def _compute_project_tag(self):
        
    # ~ def _compute_place_tag(self):
    
    # ~ analytic_account_ids = fields.Many2many('account.analytic.account', string='Analytic Accounts', readonly=False,
                                            # ~ index=True, compute="_compute_analytic_account_ids", store=True,
                                            # ~ check_company=True, copy=True)

    # ~ @api.depends('product_id', 'account_id', 'partner_id', 'date')
    # ~ def _compute_analytic_account_ids(self):
        # ~ for record in self:
            # ~ if not record.exclude_from_invoice_tab or not record.move_id.is_invoice(include_receipts=True):
                # ~ rec = self.env['account.analytic.default'].account_get_ids(
                    # ~ product_id=record.product_id.id,
                    # ~ partner_id=record.partner_id.commercial_partner_id.id or record.move_id.partner_id.commercial_partner_id.id,
                    # ~ account_id=record.account_id.id,
                    # ~ user_id=record.env.uid,
                    # ~ date=record.date,
                    # ~ company_id=record.move_id.company_id.id
                # ~ )
                # ~ if rec:
                    # ~ record.analytic_account_ids = [(6, 0, rec.analytic_id.ids)]

    # ~ def _prepare_analytic_line(self):
        # ~ """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            # ~ an analytic account. This method is intended to be extended in other modules.
            # ~ :return list of values to create analytic.line
            # ~ :rtype list
        # ~ """
        # ~ result = []
        # ~ for move_line in self:
            # ~ amount = (move_line.credit or 0.0) - (move_line.debit or 0.0)
            # ~ default_name = move_line.name or (move_line.ref or '/' + ' -- ' + (move_line.partner_id and move_line.partner_id.name or '/'))
            # ~ result.append({
                # ~ 'name': default_name,
                # ~ 'date': move_line.date,
                # ~ 'account_id': move_line.analytic_account_id.id,
                # ~ 'group_id': move_line.analytic_account_id.group_id.id,
                # ~ 'analytic_account_ids': [(6, 0, self.analytic_account_ids.ids)],
                # ~ 'tag_ids': [(6, 0, move_line._get_analytic_tag_ids())],
                # ~ 'unit_amount': move_line.quantity,
                # ~ 'product_id': move_line.product_id and move_line.product_id.id or False,
                # ~ 'product_uom_id': move_line.product_uom_id and move_line.product_uom_id.id or False,
                # ~ 'amount': amount,
                # ~ 'general_account_id': move_line.account_id.id,
                # ~ 'ref': move_line.ref,
                # ~ 'move_id': move_line.id,
                # ~ 'user_id': move_line.move_id.invoice_user_id.id or self._uid,
                # ~ 'partner_id': move_line.partner_id.id,
                # ~ 'company_id': move_line.analytic_account_id.company_id.id or move_line.move_id.company_id.id,
            # ~ })
        # ~ return result


# ~ class AccountAnalyticLine(models.Model):
    # ~ _inherit = "account.analytic.line"

    # ~ analytic_account_ids = fields.Many2many('account.analytic.account', string='Analytic Accounts',
                                            # ~ copy=True, check_company=True)
